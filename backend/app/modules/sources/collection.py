"""Public collection boundary. No real adapters are installed or enabled."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.sources.connectors.access import AllowedRoute, CollectionAuthorization
from app.modules.sources.connectors.contracts import (
    CollectionLimits,
    ConnectorFailure,
    ConnectorPage,
    ConnectorQuery,
    JobSourceConnector,
)
from app.modules.sources.connectors.http_client import CollectionCoordinator, CollectionHttpClient
from app.modules.sources.models import (
    CollectionConfig,
    CollectionReservation,
    CollectionRuntime,
    JobSource,
    SourcePreference,
)
from app.modules.sources.repository import SourceRepository
from app.shared.clock import utcnow

AdapterFactory = Callable[[CollectionHttpClient], JobSourceConnector]
CollectionAdapters = dict[str, AdapterFactory]
Guard = Callable[[AsyncSession], Awaitable[None]]
COORDINATOR = CollectionCoordinator()


class CollectionAvailability(BaseModel):
    source_id: UUID
    name: str
    eligible: bool
    reason: str
    limits: CollectionLimits


@dataclass(frozen=True)
class CollectionContext:
    execution_id: UUID
    checkpoint_id: UUID
    request_key: str
    deadline: datetime
    limits: CollectionLimits
    guard: Guard


class CollectionService:
    def __init__(self, runtime: Runtime, adapters: CollectionAdapters | None = None) -> None:
        self.runtime = runtime
        self.adapters = adapters or {}

    async def _configuration(
        self,
        session: AsyncSession,
        owner: UUID,
        source_id: UUID,
    ) -> tuple[CollectionAuthorization, CollectionLimits, str, str]:
        repo = SourceRepository(session)
        row = await repo.get(owner, source_id)
        if row is None:
            raise AppError("SOURCE_NOT_FOUND", "Source not found", 404)
        config = await session.get(CollectionConfig, source_id)
        state = await session.get(CollectionRuntime, source_id)
        preference = await repo.preference(owner, source_id)
        if config is None or row.integration_type not in {"API", "FEED"}:
            raise ConnectorFailure("AUTOMATION_NOT_CONFIGURED", "No automatic adapter configured")
        if state and state.disabled_reason:
            raise ConnectorFailure("REVIEW_REQUIRED", "Source requires review")
        auth = CollectionAuthorization(
            owner,
            source_id,
            config.enabled and bool(preference and preference.enabled),
            row.legal_status,
            row.verification,
            tuple(AllowedRoute(**route) for route in config.routes),
        )
        auth.require()
        if config.adapter_key not in self.adapters:
            raise ConnectorFailure("ADAPTER_UNAVAILABLE", "No automatic adapter registered")
        return auth, CollectionLimits.model_validate(config.limits), config.adapter_key, row.name

    async def describe(self, owner: UUID, source_id: UUID) -> CollectionAvailability:
        try:
            async with self.runtime.sessions() as session:
                _, limits, _, name = await self._configuration(session, owner, source_id)
            return CollectionAvailability(
                source_id=source_id, name=name, eligible=True, reason="READY", limits=limits
            )
        except ConnectorFailure as exc:
            async with self.runtime.sessions() as session:
                row = await SourceRepository(session).get(owner, source_id)
                if row is None:
                    raise AppError("SOURCE_NOT_FOUND", "Source not found", 404) from None
                return CollectionAvailability(
                    source_id=source_id,
                    name=row.name,
                    eligible=False,
                    reason=exc.code,
                    limits=CollectionLimits(),
                )
        except (ValueError, ValidationError):
            return CollectionAvailability(
                source_id=source_id,
                name="",
                eligible=False,
                reason="CONFIGURATION",
                limits=CollectionLimits(),
            )

    async def authorize(
        self, session: AsyncSession, owner: UUID, source_id: UUID
    ) -> CollectionLimits:
        # Serialize ingestion with policy changes; no lock spans network I/O.
        await session.execute(select(JobSource).where(JobSource.id == source_id).with_for_update())
        await session.execute(
            select(CollectionConfig)
            .where(CollectionConfig.source_id == source_id)
            .with_for_update()
        )
        await session.execute(
            select(SourcePreference)
            .where(
                SourcePreference.source_id == source_id,
                SourcePreference.user_id == owner,
            )
            .with_for_update()
        )
        await session.execute(
            select(CollectionRuntime)
            .where(CollectionRuntime.source_id == source_id)
            .with_for_update()
        )
        _, limits, _, _ = await self._configuration(session, owner, source_id)
        return limits

    async def _reserve(
        self,
        owner: UUID,
        source_id: UUID,
        context: CollectionContext,
    ) -> tuple[UUID | None, float, datetime]:
        async with self.runtime.sessions() as session, session.begin():
            await context.guard(session)
            _, current, _, _ = await self._configuration(session, owner, source_id)
            limits = stricter(context.limits, current)
            await session.execute(
                insert(CollectionRuntime)
                .values(source_id=source_id, failures=0)
                .on_conflict_do_nothing()
            )
            state = await session.scalar(
                select(CollectionRuntime)
                .where(CollectionRuntime.source_id == source_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            assert state is not None
            if state.disabled_reason:
                raise ConnectorFailure("REVIEW_REQUIRED", "Source requires review")
            now = utcnow()
            if now >= context.deadline:
                raise ConnectorFailure("DEADLINE", "Source deadline reached")
            delays = [
                (t - now).total_seconds()
                for t in (state.next_request_at, state.deferred_until)
                if t is not None
            ]
            delay = max([0.0, *delays])
            if delay >= (context.deadline - now).total_seconds():
                raise ConnectorFailure("RATE_LIMITED", "Cooldown exceeds source deadline")
            if delay > 0:
                return None, delay, context.deadline
            count, wire, body = (
                await session.execute(
                    select(
                        func.count(),
                        func.coalesce(func.sum(CollectionReservation.wire_bytes), 0),
                        func.coalesce(func.sum(CollectionReservation.body_bytes), 0),
                    ).where(
                        CollectionReservation.execution_id == context.execution_id,
                        CollectionReservation.source_id == source_id,
                    )
                )
            ).one()
            if count >= limits.max_requests:
                raise ConnectorFailure("REQUEST_LIMIT", "Request budget reached")
            if (
                wire + limits.max_wire_bytes > limits.max_total_bytes
                or body + limits.max_body_bytes > limits.max_total_bytes
            ):
                raise ConnectorFailure("SIZE_LIMIT", "Durable byte budget reached")
            reservation = CollectionReservation(
                source_id=source_id,
                execution_id=context.execution_id,
                checkpoint_id=context.checkpoint_id,
                request_key=context.request_key,
                ordinal=count,
                wire_bytes=limits.max_wire_bytes,
                body_bytes=limits.max_body_bytes,
            )
            session.add(reservation)
            await session.flush()
            attempt_until = min(
                context.deadline, now + timedelta(seconds=limits.timeout_seconds + 10)
            )
            state.active_reservation_id = reservation.id
            # A crashed request holds the slot until its bounded attempt expires.
            state.next_request_at = attempt_until + timedelta(seconds=limits.min_interval_seconds)
            return reservation.id, 0, attempt_until

    async def settle(self, identifier: UUID, wire: int, body: int, interval: float = 0) -> None:
        async with self.runtime.sessions() as session, session.begin():
            row = await session.get(CollectionReservation, identifier, with_for_update=True)
            if row is not None and not row.settled:
                row.wire_bytes = min(row.wire_bytes, max(0, wire))
                row.body_bytes = min(row.body_bytes, max(0, body))
                row.settled = True
                state = await session.get(CollectionRuntime, row.source_id, with_for_update=True)
                config = await session.get(CollectionConfig, row.source_id)
                if state is not None and state.active_reservation_id == identifier:
                    current = CollectionLimits.model_validate(config.limits if config else {})
                    state.next_request_at = utcnow() + timedelta(
                        seconds=max(interval, current.min_interval_seconds)
                    )
                    state.active_reservation_id = None

    async def outcome(self, source_id: UUID, code: str | None, delay: float | None = None) -> None:
        async with self.runtime.sessions() as session, session.begin():
            await session.execute(
                insert(CollectionRuntime)
                .values(source_id=source_id, failures=0)
                .on_conflict_do_nothing()
            )
            row = await session.get(CollectionRuntime, source_id, with_for_update=True)
            assert row is not None
            if delay is not None:
                deferred = utcnow() + timedelta(seconds=min(86400, max(0, delay)))
                row.deferred_until = max(row.deferred_until or deferred, deferred)
            if code in {"AUTH", "BLOCKED"}:
                row.disabled_reason = code
            elif code == "SCHEMA":
                row.failures += 1
                if row.failures >= 3:
                    row.disabled_reason = code
            elif code is None:
                row.failures = 0

    async def client(
        self,
        owner: UUID,
        source_id: UUID,
        context: CollectionContext,
    ) -> tuple[CollectionHttpClient, JobSourceConnector]:
        async with self.runtime.sessions() as session:
            _, current, key, _ = await self._configuration(session, owner, source_id)
        limits = stricter(context.limits, current)
        attempt_until: datetime | None = None

        async def authorization() -> CollectionAuthorization:
            async with self.runtime.sessions() as session:
                await context.guard(session)
                auth, current, _, _ = await self._configuration(session, owner, source_id)
                client.limits = stricter(client.limits, current)
                if attempt_until is not None:
                    remaining = (attempt_until - utcnow()).total_seconds()
                    if remaining <= 0:
                        raise ConnectorFailure("DEADLINE", "HTTP attempt expired")
                    client.limits = client.limits.model_copy(
                        update={
                            "timeout_seconds": min(client.limits.timeout_seconds, remaining),
                        }
                    )
                client.budget.limits = client.limits
                return auth

        async def reserve() -> UUID:
            nonlocal attempt_until
            attempt_until = None
            while True:
                identifier, delay, until = await self._reserve(owner, source_id, context)
                if identifier is not None:
                    attempt_until = until
                    # Refresh transport limits after the durable reservation too.
                    # Permission withdrawal consumes the reservation conservatively.
                    await authorization()
                    return identifier
                await asyncio.sleep(min(delay, 1))

        async def settle(identifier: UUID, wire: int, body: int) -> None:
            nonlocal attempt_until
            await self.settle(identifier, wire, body, context.limits.min_interval_seconds)
            attempt_until = None

        async def defer(delay: float) -> None:
            await self.outcome(source_id, "RATE_LIMITED", delay)

        client = CollectionHttpClient(
            authorization,
            limits,
            COORDINATOR,
            reserve=reserve,
            settle=settle,
            defer=defer,
        )
        client.budget.started -= max(
            0, limits.duration_seconds - (context.deadline - utcnow()).total_seconds()
        )
        return client, self.adapters[key](client)

    async def fetch_page(
        self,
        owner: UUID,
        source_id: UUID,
        query: ConnectorQuery,
        context: CollectionContext,
    ) -> ConnectorPage:
        client, adapter = await self.client(owner, source_id, context)
        try:
            page = await adapter.fetch_page(query)
            await self.outcome(source_id, None)
            return page
        except ConnectorFailure as exc:
            await self.outcome(source_id, exc.code, exc.retry_after)
            raise
        except (ValueError, ValidationError):
            await self.outcome(source_id, "SCHEMA")
            raise ConnectorFailure("SCHEMA", "Source response schema changed") from None
        finally:
            await client.aclose()

    async def test(self, owner: UUID, source_id: UUID) -> CollectionAvailability:
        availability = await self.describe(owner, source_id)
        if not availability.eligible:
            return availability

        async def guard(session: AsyncSession) -> None:
            return None

        context = CollectionContext(
            uuid4(), uuid4(), "0" * 64, utcnow() + timedelta(seconds=30), availability.limits, guard
        )
        client, adapter = await self.client(owner, source_id, context)
        try:
            health = await adapter.health_check()
            return availability.model_copy(update={"reason": health, "eligible": health == "READY"})
        except ConnectorFailure as exc:
            await self.outcome(source_id, exc.code, exc.retry_after)
            return availability.model_copy(update={"eligible": False, "reason": exc.code})
        finally:
            await client.aclose()


def stricter(left: CollectionLimits, right: CollectionLimits) -> CollectionLimits:
    a, b = left.model_dump(), right.model_dump()
    return CollectionLimits.model_validate(
        {
            key: max(a[key], b[key]) if key == "min_interval_seconds" else min(a[key], b[key])
            for key in a
        }
    )
