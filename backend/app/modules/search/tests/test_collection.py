import asyncio
import json
from datetime import timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.listings import (
    CollectedJob,
    CollectionPageInput,
    CollectionReceipt,
    ImportJob,
    ListingService,
    ingest_collection_page,
)
from app.modules.listings.models import CollectionObservation, CollectionPage
from app.modules.search.execution_schemas import ExecutionInput, ExecutionView
from app.modules.search.executions import ExecutionService
from app.modules.search.models import CollectionCheckpoint, SearchTask
from app.modules.search.queue import SearchQueue
from app.modules.search.schemas import ProfileInput, SearchCriteria
from app.modules.search.service import SearchService
from app.modules.search.tests.test_queue import lookup, prepare
from app.modules.sources import (
    CollectionAdapters,
    CollectionService,
    ConnectorPage,
    NormalizedListing,
)
from app.modules.sources.connectors.contracts import Capabilities
from app.modules.sources.models import (
    CollectionConfig,
    CollectionReservation,
    CollectionRuntime,
    JobSource,
    SourcePreference,
)
from app.modules.sources.schemas import SourceCreate
from app.modules.sources.service import SourceService
from app.shared.clock import utcnow

pytestmark = pytest.mark.integration


class FakeAdapter:
    def __init__(self, client: Any, handler: Any) -> None:
        self.client = client
        client._transport = httpx.MockTransport(handler)

    def capabilities(self) -> Capabilities:
        return Capabilities(automated=True, pagination=True)

    async def health_check(self) -> Literal["READY"]:
        await self.client.get("https://collection.example/jobs")
        return "READY"

    async def fetch_page(self, query: Any) -> ConnectorPage:
        response = await self.client.get(
            "https://collection.example/jobs?cursor=" + (query.cursor or "")
        )
        import json

        return ConnectorPage.model_validate(json.loads(response.body))

    async def fetch(self, query: Any) -> list[NormalizedListing]:
        return (await self.fetch_page(query)).items

    def normalize(self, raw: Any) -> NormalizedListing:
        return NormalizedListing.model_validate(raw)


async def setup(
    database: Runtime, handler: Any
) -> tuple[UUID, UUID, UUID, CollectionService, CollectionAdapters]:
    user, _ = await prepare(database)
    async with database.sessions() as session:
        source = await SourceService(session).create(
            user,
            SourceCreate(
                name="Synthetic collection", homepage="https://collection.example/", region="GLOBAL"
            ),
        )
    async with database.sessions() as session:
        profile = await SearchService(session).create(
            user,
            ProfileInput(
                name="Collection",
                criteria=SearchCriteria(source_ids=[source.id], experience_levels=[]),
            ),
        )
    now = utcnow().isoformat()
    async with database.sessions() as session, session.begin():
        row = await session.get(JobSource, source.id)
        assert row is not None
        row.integration_type = "API"
        row.legal_status = "PERMITTED"
        row.verification = {
            "api_url": "https://collection.example/jobs",
            "terms_url": "https://collection.example/terms",
            "access_method": "synthetic",
            "allowed_usage": "fixtures",
            "rate_limit": "fixture",
            "reviewer": "test fixture",
            "evidence": "synthetic only",
            "robots_allowed": True,
            "access_confirmed": True,
            "robots_checked_at": now,
            "terms_reviewed_at": now,
        }
        session.add(SourcePreference(user_id=user, source_id=source.id, enabled=True))
        session.add(
            CollectionConfig(
                source_id=source.id,
                adapter_key="fixture",
                enabled=True,
                routes=[{"host": "collection.example", "path_prefix": "/jobs"}],
                limits={"min_interval_seconds": 0.01},
            )
        )
    adapters: CollectionAdapters = {"fixture": lambda client: FakeAdapter(client, handler)}
    service = CollectionService(database, adapters)
    return user, profile.id, source.id, service, adapters


async def request(
    database: Runtime, user: UUID, profile: UUID, service: CollectionService, maximum: int = 10
) -> ExecutionView:
    async with database.sessions() as session:
        return await ExecutionService(session, service).request(
            user,
            profile,
            lookup(database),
            ExecutionInput(profile_id=profile, scope="COLLECTED_OFFERS", max_results=maximum),
        )


async def view(database: Runtime, user: UUID, execution: UUID) -> ExecutionView:
    async with database.sessions() as session:
        return await ExecutionService(session).get(user, execution)


def job(path: str = "a", **extra: Any) -> dict[str, Any]:
    return {"original_url": "https://collection.example/" + path, "title": "Python", **extra}


def page(items: Any = None, **extra: Any) -> httpx.Response:
    return httpx.Response(
        200, stream=httpx.ByteStream(json.dumps({"items": items or [], **extra}).encode())
    )


async def test_collection_pipeline_real_queue_and_immutable_manual_content(
    database: Runtime,
) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        return page(
            [
                job(
                    description="Collected text",
                    employment_types=["FULL_TIME"],
                    published_date="2026-11-08",
                    publication_precision="DATE",
                )
            ]
        )

    user, profile, source, service, adapters = await setup(database, handler)
    async with database.sessions() as session, session.begin():
        from app.modules.listings.repository import ListingRepository
        from app.shared.source_reference import SourceReference

        await ListingRepository(session).import_one(
            user,
            SourceReference(source, "Synthetic", True),
            ImportJob(**job(description="Confirmed manual original")),
        )
    execution = await request(database, user, profile, service)
    assert execution.scope == "COLLECTED_OFFERS"
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert final.status == "SUCCEEDED" and final.counts["existing"] == 1, final.model_dump_json()
    assert final.sources[0].counts == {
        "pages": 1,
        "collected": 1,
        "created": 0,
        "existing": 1,
        "invalid": 0,
    }
    assert len(calls) == 1
    async with database.sessions() as session:
        listings = await ListingService(session).page(user, 20, 0)
        assert (
            next(j for j in listings.items if j.source_id == source).description
            == "Confirmed manual original"
        )
        obs = await session.scalar(select(CollectionObservation))
        assert obs is not None
        metadata = obs.payload["metadata"]
        assert isinstance(metadata, dict) and metadata["publication_precision"] == "DATE"
        assert (await session.scalar(select(func.count()).select_from(CollectionReservation))) == 1
    assert "cursor=" not in final.model_dump_json()


async def test_crash_recovery_from_committed_page_without_duplicate_ingestion(
    database: Runtime,
) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.params.get("cursor"))
        if len(calls) == 2:
            raise asyncio.CancelledError
        return page(
            [job("a" if not req.url.params.get("cursor") else "b")],
            next_cursor="next" if not req.url.params.get("cursor") else None,
        )

    user, profile, source, service, adapters = await setup(database, handler)
    execution = await request(database, user, profile, service)
    queue = SearchQueue(database, adapters=adapters)
    with pytest.raises(asyncio.CancelledError):
        await queue.run_once()
    async with database.sessions() as session, session.begin():
        cp = await session.scalar(
            select(CollectionCheckpoint).where(CollectionCheckpoint.execution_id == execution.id)
        )
        assert cp is not None
        assert cp.collected == 1 and cp.cursor == "next"
        # Simulate the same elapsed recovery interval as the expired heartbeat.
        await session.execute(
            update(CollectionRuntime).values(next_request_at=utcnow() - timedelta(minutes=3))
        )
        await session.execute(
            update(SearchTask)
            .where(SearchTask.execution_id == execution.id)
            .values(heartbeat_at=utcnow() - timedelta(minutes=3))
        )
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert final.status == "SUCCEEDED" and final.counts["created"] == 2
    assert calls == ["", "next", "next"]
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CollectionPage)) == 2
        assert await session.scalar(select(func.count()).select_from(CollectionObservation)) == 2
        reservations = list((await session.scalars(select(CollectionReservation))).all())
        assert len(reservations) == 3 and sum(not r.settled for r in reservations) == 1


@pytest.mark.parametrize(
    "mode,expected", [("cancel", "CANCELLED"), ("revoke", "FAILED"), ("lease", "RUNNING")]
)
async def test_inflight_cancellation_revocation_and_lost_lease(
    database: Runtime, mode: str, expected: str
) -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        async with database.sessions() as session, session.begin():
            if mode == "cancel":
                from app.modules.search.models import SearchExecution

                await session.execute(update(SearchExecution).values(cancel_requested=True))
            elif mode == "revoke":
                await session.execute(update(CollectionConfig).values(enabled=False))
            else:
                await session.execute(update(SearchTask).values(lease_token=uuid4()))
        return page([job()])

    user, profile, _, service, adapters = await setup(database, handler)
    execution = await request(database, user, profile, service)
    await SearchQueue(database, adapters=adapters).run_once()
    assert (await view(database, user, execution.id)).status == expected
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CollectionPage)) == 0


@pytest.mark.parametrize(
    "status,reason", [(401, "AUTH"), (403, "BLOCKED"), (429, "RATE_LIMITED"), (500, "HTTP_ERROR")]
)
async def test_network_error_and_persistent_cooldown(
    database: Runtime, status: int, reason: str
) -> None:
    user, profile, source, service, adapters = await setup(
        database, lambda r: httpx.Response(status, headers={"retry-after": "999"})
    )
    execution = await request(database, user, profile, service)
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert final.status == "FAILED" and final.reason == reason
    async with database.sessions() as session:
        state = await session.get(CollectionRuntime, source)
        assert state is not None
        if status in {401, 403}:
            assert state.disabled_reason == reason
        if status == 429:
            assert state.deferred_until is not None and state.deferred_until > utcnow()


async def test_result_limit_and_repeated_cursor_are_explicit(database: Runtime) -> None:
    user, profile, _, service, adapters = await setup(
        database, lambda r: page([job()], next_cursor="same")
    )
    execution = await request(database, user, profile, service, maximum=1)
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert (
        final.status == "PARTIAL"
        and final.reason == "RESULT_LIMIT"
        and final.counts["collected"] == 1
    )
    execution = await request(database, user, profile, service)
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert final.status == "PARTIAL" and final.reason == "PAGINATION_LOOP"
    assert final.counts["created"] == 0 and final.counts["existing"] == 2


async def test_page_receipt_replay_and_rollback_are_atomic(database: Runtime) -> None:
    user, profile, source, _, _ = await setup(database, lambda r: page())
    body = CollectionPageInput(
        execution_id=uuid4(),
        checkpoint_id=uuid4(),
        source_id=source,
        source_name="Synthetic",
        request_key="a" * 64,
        query_hash="b" * 64,
        items=[CollectedJob(job=ImportJob(**job()), metadata={"publication_precision": "UNKNOWN"})],
    )
    async with database.sessions() as session:
        with pytest.raises(RuntimeError):
            async with session.begin():
                await ingest_collection_page(session, user, body)
                raise RuntimeError("Simulated crash before commit")
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CollectionPage)) == 0
    async with database.sessions() as session, session.begin():
        first = await ingest_collection_page(session, user, body)
    async with database.sessions() as session, session.begin():
        second = await ingest_collection_page(session, user, body)
    assert first == second and first.created == 1
    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CollectionObservation)) == 1


async def test_configuration_refuses_missing_adapters_expired_permission_and_other_owner(
    database: Runtime,
) -> None:
    user, profile, source, service, _ = await setup(database, lambda r: page())
    assert (await service.describe(user, source)).eligible
    assert not (await CollectionService(database).describe(user, source)).eligible
    with pytest.raises(AppError):
        await service.describe(uuid4(), source)
    async with database.sessions() as session, session.begin():
        row = await session.get(JobSource, source)
        assert row is not None
        row.verification = {
            **row.verification,
            "terms_reviewed_at": (utcnow() - timedelta(days=91)).isoformat(),
        }
    assert not (await service.describe(user, source)).eligible
    with pytest.raises(AppError):
        await request(database, user, profile, service)


@pytest.mark.parametrize("maximum", [0, 501])
def test_invalid_limits(maximum: int) -> None:
    with pytest.raises(ValidationError):
        ExecutionInput(profile_id=uuid4(), scope="COLLECTED_OFFERS", max_results=maximum)


def test_legacy_request_rejects_collection_options() -> None:
    assert ExecutionInput(profile_id=uuid4()).scope == "IMPORTED_OFFERS"
    with pytest.raises(ValidationError):
        ExecutionInput(profile_id=uuid4(), max_results=10)


@pytest.mark.parametrize(
    "limit,reason",
    [("requests", "REQUEST_LIMIT"), ("pages", "PAGE_LIMIT"), ("bytes", "SIZE_LIMIT")],
)
async def test_durable_limits_are_not_reset_between_pages(
    database: Runtime, limit: str, reason: str
) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return page([job()], next_cursor=str(len(calls)))

    user, profile, source, service, adapters = await setup(database, handler)
    async with database.sessions() as session, session.begin():
        config = await session.get(CollectionConfig, source)
        assert config is not None
        config.limits = {
            "min_interval_seconds": 0.01,
            **(
                {"max_requests": 1}
                if limit == "requests"
                else {"max_pages": 1}
                if limit == "pages"
                else {"max_total_bytes": 1}
            ),
        }
    execution = await request(database, user, profile, service)
    await SearchQueue(database, adapters=adapters).run_once()
    final = await view(database, user, execution.id)
    assert final.reason == reason
    assert len(calls) == (0 if limit == "bytes" else 1)
    assert final.status == ("FAILED" if limit == "bytes" else "PARTIAL")


async def test_global_result_budget_shared_between_sources(database: Runtime) -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return page([job()])

    user, profile, source, service, adapters = await setup(database, handler)
    async with database.sessions() as session, session.begin():
        original = await session.get(JobSource, source)
        assert original is not None
        other = JobSource(
            user_id=user,
            slug="synthetic-second",
            name="Second fixture",
            homepage=original.homepage,
            integration_type="API",
            legal_status="PERMITTED",
            verification=original.verification,
        )
        session.add(other)
        await session.flush()
        other_id = other.id
        session.add(
            CollectionConfig(
                source_id=other.id,
                adapter_key="fixture",
                enabled=True,
                routes=[{"host": "collection.example", "path_prefix": "/jobs"}],
                limits={"min_interval_seconds": 0.01},
            )
        )
        session.add(SourcePreference(user_id=user, source_id=other.id, enabled=True))
    async with database.sessions() as session:
        await SearchService(session).update(
            user,
            profile,
            ProfileInput(
                name="Two sources",
                criteria=SearchCriteria(source_ids=[source, other_id], experience_levels=[]),
            ),
        )
    execution = await request(database, user, profile, service, maximum=1)
    outcomes = await asyncio.gather(
        SearchQueue(database, adapters=adapters).run_once(),
        SearchQueue(database, adapters=adapters).run_once(),
    )
    assert outcomes.count(True) == 1 and len(calls) == 1
    final = await view(database, user, execution.id)
    assert final.status == "PARTIAL" and final.counts["collected"] == 1


async def test_crash_between_ingestion_and_checkpoint_rolls_back_everything(
    database: Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, profile, _, service, adapters = await setup(database, lambda r: page([job()]))
    execution = await request(database, user, profile, service)
    import app.modules.search.collection as orchestrator

    original = ingest_collection_page

    async def crash(*args: Any) -> CollectionReceipt:
        await original(*args)
        raise RuntimeError("Synthetic crash before checkpoint write")

    monkeypatch.setattr(orchestrator, "ingest_collection_page", crash)
    await SearchQueue(database, adapters=adapters).run_once()
    async with database.sessions() as session:
        cp = await session.scalar(
            select(CollectionCheckpoint).where(CollectionCheckpoint.execution_id == execution.id)
        )
        assert cp is not None
        assert cp.collected == 0 and cp.cursor is None
        assert await session.scalar(select(func.count()).select_from(CollectionPage)) == 0
        assert await session.scalar(select(func.count()).select_from(CollectionObservation)) == 0


async def test_schema_failures_auto_disable_without_retries(database: Runtime) -> None:
    user, profile, source, service, adapters = await setup(
        database, lambda r: httpx.Response(200, stream=httpx.ByteStream(b"{}invalid"))
    )
    for _ in range(3):
        execution = await request(database, user, profile, service)
        await SearchQueue(database, adapters=adapters).run_once()
        assert (await view(database, user, execution.id)).reason == "SCHEMA"
    assert (await service.describe(user, source)).reason == "REVIEW_REQUIRED"


async def test_api_capabilities_and_denial_do_not_reveal_secret_errors(database: Runtime) -> None:
    from app.main import create_app

    user, profile = await prepare(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            from app.modules.search.tests.test_queue import SOURCE

            assert (await client.get(f"/api/sources/{SOURCE}/collection")).status_code == 401
            assert (
                await client.post(
                    "/api/auth/login",
                    json={"email": "queue@example.test", "password": "fixture-password-for-queue"},
                )
            ).status_code == 200
            response = await client.get(f"/api/sources/{SOURCE}/collection")
            assert response.status_code == 200 and not response.json()["eligible"]
            assert not (await client.post(f"/api/sources/{SOURCE}/collection/test")).json()[
                "eligible"
            ]
            denied = await client.post(
                "/api/search/executions",
                json={"profile_id": str(profile), "scope": "COLLECTED_OFFERS", "max_results": 10},
            )
            assert denied.status_code == 409
            assert "DATABASE_URL" not in denied.text and "cursor" not in response.text
            invalid = await client.post(
                "/api/search/executions", json={"profile_id": str(profile), "max_results": 10}
            )
            assert invalid.status_code == 422
    finally:
        await app.state.runtime.engine.dispose()
