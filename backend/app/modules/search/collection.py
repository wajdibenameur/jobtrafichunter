"""Durable COLLECT stage in the existing queue; network runs outside transactions."""

import hashlib
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.listings import (
    CollectedJob,
    CollectionPageInput,
    ImportJob,
    ingest_collection_page,
)
from app.modules.search.models import (
    CollectionCheckpoint,
    CollectionPlan,
    SearchExecution,
    SearchTask,
)
from app.modules.search.schemas import SearchCriteria
from app.modules.sources import (
    CollectionContext,
    CollectionLimits,
    CollectionService,
    ConnectorFailure,
    ConnectorQuery,
    stricter,
)
from app.shared.clock import utcnow

if TYPE_CHECKING:
    from app.modules.search.queue import TaskLease

Fence = Callable[[AsyncSession, "TaskLease"], Awaitable[tuple[SearchTask, SearchExecution]]]


class CollectionStopped(Exception):
    pass


class Collector:
    def __init__(self, runtime: Runtime, service: CollectionService, fence: Fence) -> None:
        self.runtime, self.service, self.fence = runtime, service, fence

    async def run(self, lease: "TaskLease", criteria: SearchCriteria) -> None:
        async with self.runtime.sessions() as session:
            task = await session.get(SearchTask, lease.task_id)
            if task is None or task.stage != "COLLECT":
                return
            identifiers = list(
                (
                    await session.scalars(
                        select(CollectionCheckpoint.id)
                        .where(CollectionCheckpoint.execution_id == lease.execution_id)
                        .order_by(CollectionCheckpoint.source_id)
                    )
                ).all()
            )
        for identifier in identifiers:
            while True:
                async with self.runtime.sessions() as session, session.begin():
                    task, execution = await self.fence(session, lease)
                    if execution.cancel_requested:
                        raise CollectionStopped
                    cp = await session.get(CollectionCheckpoint, identifier)
                    plan = await session.get(CollectionPlan, lease.execution_id)
                    assert cp is not None and plan is not None
                    if cp.state not in {"PENDING", "RUNNING"}:
                        break
                    total = int(
                        await session.scalar(
                            select(
                                func.coalesce(func.sum(CollectionCheckpoint.collected), 0)
                            ).where(CollectionCheckpoint.execution_id == lease.execution_id)
                        )
                        or 0
                    )
                    try:
                        available = await self.service.describe(lease.user_id, cp.source_id)
                    except AppError:
                        cp.state, cp.reason = "PARTIAL", "SOURCE_UNAVAILABLE"
                        continue
                    limits = stricter(
                        CollectionLimits.model_validate(plan.sources[str(cp.source_id)]),
                        available.limits,
                    )
                    cp.source_deadline = cp.source_deadline or min(
                        plan.deadline, utcnow() + timedelta(seconds=limits.duration_seconds)
                    )
                    reason = (
                        available.reason
                        if not available.eligible
                        else "RESULT_LIMIT"
                        if total >= plan.max_results
                        else "PAGE_LIMIT"
                        if cp.page_index >= limits.max_pages
                        else "DEADLINE"
                        if utcnow() >= cp.source_deadline
                        else None
                    )
                    if reason:
                        cp.state, cp.reason = "PARTIAL", reason
                        continue
                    remaining = min(plan.max_results - total, limits.max_results - cp.collected)
                    if remaining <= 0:
                        cp.state, cp.reason = "PARTIAL", "RESULT_LIMIT"
                        continue
                    query = ConnectorQuery(
                        keywords=" ".join([*criteria.titles, *criteria.include_keywords])[:200],
                        location=" ".join([*criteria.countries, *criteria.cities])[:200],
                        cursor=cp.cursor,
                        limit=remaining,
                        publication_minutes=criteria.publication_minutes
                        or (criteria.publication_days * 1440 or None),
                    )
                    cp.state = "RUNNING"
                    request_key = hashlib.sha256(
                        f"1:{lease.execution_id}:{cp.source_id}:{cp.query_hash}:{cp.cursor}:{cp.page_index}".encode()
                    ).hexdigest()
                    source_id, query_hash, deadline = (
                        cp.source_id,
                        cp.query_hash,
                        cp.source_deadline,
                    )

                async def guard(session: AsyncSession) -> None:
                    _, active = await self.fence(session, lease)
                    if active.cancel_requested:
                        raise CollectionStopped

                context = CollectionContext(
                    lease.execution_id, identifier, request_key, deadline, limits, guard
                )
                try:
                    page = await self.service.fetch_page(lease.user_id, source_id, query, context)
                    if len(page.items) > query.limit:
                        raise ConnectorFailure("RESULT_LIMIT", "Adapter exceeded result limit")
                    async with self.runtime.sessions() as session, session.begin():
                        await guard(session)
                        current = await self.service.authorize(session, lease.user_id, source_id)
                        cp = await session.get(CollectionCheckpoint, identifier)
                        assert cp is not None
                        if len(page.items) + cp.collected > current.max_results:
                            raise ConnectorFailure("RESULT_LIMIT", "Current source limit reached")
                        if cp.page_index >= current.max_pages:
                            raise ConnectorFailure("PAGE_LIMIT", "Current page limit reached")
                        # A late response after a source deadline may not advance the checkpoint.
                        if utcnow() >= deadline:
                            raise ConnectorFailure("DEADLINE", "Source deadline reached")
                        items = []
                        for item in page.items:
                            location = item.locations[0] if item.locations else None
                            items.append(
                                CollectedJob(
                                    job=ImportJob(
                                        original_url=item.original_url,
                                        application_url=item.application_url,
                                        source_job_id=item.source_job_id,
                                        title=item.title,
                                        company=item.company,
                                        description=item.description,
                                        published_at=item.published_at,
                                        country=location.country if location else None,
                                        city=location.city if location else None,
                                        work_mode=item.work_mode,
                                    ),
                                    metadata=item.model_dump(mode="json"),
                                )
                            )
                        receipt = await ingest_collection_page(
                            session,
                            lease.user_id,
                            CollectionPageInput(
                                execution_id=lease.execution_id,
                                checkpoint_id=identifier,
                                source_id=source_id,
                                source_name=available.name,
                                request_key=request_key,
                                query_hash=query_hash,
                                items=items,
                            ),
                        )
                        cp.page_index += 1
                        cp.collected += len(items)
                        cp.created += receipt.created
                        cp.existing += receipt.existing
                        cp.invalid += page.invalid_count
                        cursor_hash = hashlib.sha256((page.next_cursor or "").encode()).hexdigest()
                        if page.next_cursor is not None and (
                            page.next_cursor == cp.cursor or cursor_hash in cp.seen_cursors
                        ):
                            cp.state, cp.reason = "PARTIAL", "PAGINATION_LOOP"
                        elif page.partial or page.truncated or page.invalid_count:
                            cp.state, cp.reason = "PARTIAL", "SOURCE_PARTIAL"
                        elif page.next_cursor is None:
                            cp.state, cp.reason = "SUCCEEDED", None
                        else:
                            cp.seen_cursors = [*cp.seen_cursors, cursor_hash]
                        cp.cursor = page.next_cursor
                except (ConnectorFailure, AppError) as exc:
                    async with self.runtime.sessions() as session, session.begin():
                        await guard(session)
                        cp = await session.get(CollectionCheckpoint, identifier)
                        assert cp is not None
                        cp.state, cp.reason = "PARTIAL", safe_reason(exc.code)
        async with self.runtime.sessions() as session, session.begin():
            task, execution = await self.fence(session, lease)
            if execution.cancel_requested:
                raise CollectionStopped
            checkpoints = list(
                (
                    await session.scalars(
                        select(CollectionCheckpoint).where(
                            CollectionCheckpoint.execution_id == lease.execution_id
                        )
                    )
                ).all()
            )
            execution.counts = {
                **execution.counts,
                "collected": sum(c.collected for c in checkpoints),
                "created": sum(c.created for c in checkpoints),
                "existing": sum(c.existing for c in checkpoints),
            }
            failures = [c for c in checkpoints if c.state != "SUCCEEDED"]
            execution.reason = failures[0].reason if failures else None
            if failures and not any(c.page_index for c in checkpoints):
                task.status = execution.status = (
                    "TIMED_OUT" if execution.reason == "DEADLINE" else "FAILED"
                )
                task.lease_token = None
                task.locked_by = None
                execution.finished_at = utcnow()
                raise_after = True
            else:
                task.stage = "SCAN"
                raise_after = False
        if raise_after:
            raise CollectionStopped


def safe_reason(code: str) -> str:
    allowed = {
        "AUTH",
        "BLOCKED",
        "SCHEMA",
        "TIMEOUT",
        "DEADLINE",
        "RATE_LIMITED",
        "REQUEST_LIMIT",
        "PAGE_LIMIT",
        "RESULT_LIMIT",
        "SIZE_LIMIT",
        "NOT_PERMITTED",
        "REVIEW_REQUIRED",
        "ADAPTER_UNAVAILABLE",
        "UNAVAILABLE",
        "HTTP_ERROR",
        "UNSAFE_URL",
        "PROTOCOL_ERROR",
        "REDIRECT_LIMIT",
        "UNSUPPORTED_ENCODING",
        "IMPORT_CONFLICT",
    }
    return code if code in allowed else "COLLECTION_FAILED"
