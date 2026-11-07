import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import update

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.listings import ListingCatalog, ListingService
from app.modules.listings.schemas import ImportJob, ImportRequest
from app.modules.search.executions import ExecutionService
from app.modules.search.models import SearchTask
from app.modules.search.queue import LeaseLost, SearchQueue
from app.modules.search.schemas import ProfileInput, SearchCriteria
from app.modules.search.service import SearchService
from app.modules.sources import SourceService
from app.shared.clock import utcnow
from app.shared.source_reference import SourceLookup, SourceReference

pytestmark = pytest.mark.integration
SOURCE = UUID("10000000-0000-4000-8000-000000000001")


async def prepare(database: Runtime) -> tuple[UUID, UUID]:
    async with database.sessions() as session:
        user = (
            await AuthService(session, database.settings).setup_owner(
                "queue@example.test", "fixture-password-for-queue"
            )
        ).id
    async with database.sessions() as session:
        source = await SourceService(session).resolve(user, SOURCE)
    async with database.sessions() as session:
        await ListingService(session).import_jobs(
            user,
            source,
            ImportRequest(
                source_id=SOURCE,
                confirm=True,
                jobs=[
                    ImportJob(original_url="https://example.test/a", title="Python"),
                    ImportJob(original_url="https://example.test/b", title="Other"),
                ],
            ),
        )
    async with database.sessions() as session:
        profile = await SearchService(session).create(
            user, ProfileInput(name="Local", criteria=SearchCriteria(source_ids=[SOURCE]))
        )
    return user, profile.id


def lookup(database: Runtime) -> SourceLookup:
    async def resolve(user_id: UUID, source_id: UUID) -> SourceReference:
        async with database.sessions() as session:
            return await SourceService(session).resolve(user_id, source_id)

    return resolve


async def request(database: Runtime, user: UUID, profile: UUID) -> UUID:
    async with database.sessions() as session:
        return (await ExecutionService(session).request(user, profile, lookup(database))).id


async def test_two_workers_one_claim_and_immutable_results(database: Runtime) -> None:
    user, profile = await prepare(database)
    identifier = await request(database, user, profile)
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await ExecutionService(session).request(user, profile, lookup(database))
        assert error.value.code == "SEARCH_ALREADY_ACTIVE"
    results = await asyncio.gather(
        SearchQueue(database).run_once(), SearchQueue(database).run_once()
    )
    assert results.count(True) == 1
    async with database.sessions() as session:
        view = await ExecutionService(session).get(user, identifier)
        assert view.status == "SUCCEEDED" and view.counts["results"] == 2
        assert all(
            source.status == "SKIPPED" and source.reason == "MANUAL_ONLY" for source in view.sources
        )
    async with database.sessions() as session:
        source = await SourceService(session).resolve(user, SOURCE)
    async with database.sessions() as session:
        await ListingService(session).import_jobs(
            user,
            source,
            ImportRequest(
                source_id=SOURCE,
                confirm=True,
                jobs=[
                    ImportJob(
                        original_url="https://example.test/a", title="Changed after execution"
                    )
                ],
            ),
        )
    async with database.sessions() as session:
        page = await ExecutionService(session).results(user, identifier, 20, 0)
        assert {item.listing.title for item in page.items} == {"Python", "Other"}
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await ExecutionService(session).get(uuid4(), identifier)
        assert error.value.status == 404


async def test_expired_lease_resumes_checkpoint_and_fences_old_worker(database: Runtime) -> None:
    user, profile = await prepare(database)
    identifier = await request(database, user, profile)
    first = SearchQueue(database, "worker-one")
    lease = await first.claim()
    assert lease is not None
    async with database.sessions() as session:
        scan = await ListingCatalog(session).scan(user, [SOURCE])
    await first._save_snapshot(lease, scan)
    groups = sorted(scan.groups, key=lambda group: str(group.id))
    criteria, _, _, _ = await first._load(lease)
    await first._batch(lease, groups[:1], 0, criteria, False, False)
    async with database.sessions() as session, session.begin():
        await session.execute(
            update(SearchTask)
            .where(SearchTask.id == lease.task_id)
            .values(heartbeat_at=utcnow() - timedelta(minutes=3))
        )
    second = SearchQueue(database, "worker-two")
    renewed = await second.claim()
    assert renewed is not None and renewed.token != lease.token
    assert not await first.heartbeat(lease)
    with pytest.raises(LeaseLost):
        await first._batch(lease, groups[1:], 1, criteria, False, True)
    criteria, snapshot, cursor, _ = await second._load(renewed)
    assert cursor == 1
    await second._process(renewed, criteria, snapshot, cursor)
    async with database.sessions() as session:
        view = await ExecutionService(session).get(user, identifier)
        assert view.status == "SUCCEEDED" and view.attempt == 2 and view.counts["results"] == 2


async def test_cancellation_retains_results_and_retries_are_bounded(database: Runtime) -> None:
    user, profile = await prepare(database)
    identifier = await request(database, user, profile)
    queue = SearchQueue(database)
    lease = await queue.claim()
    assert lease is not None
    async with database.sessions() as session:
        scan = await ListingCatalog(session).scan(user, [SOURCE])
    criteria, _, _, _ = await queue._load(lease)
    await queue._save_snapshot(lease, scan)
    await queue._batch(lease, scan.groups[:1], 0, criteria, False, False)
    async with database.sessions() as session:
        await ExecutionService(session).cancel(user, identifier)
    await queue._batch(lease, scan.groups[1:], 1, criteria, False, True)
    async with database.sessions() as session:
        view = await ExecutionService(session).get(user, identifier)
        assert view.status == "CANCELLED" and view.counts["results"] == 1
    identifier = await request(database, user, profile)
    for _ in range(3):
        lease = await queue.claim()
        assert lease is not None
        await queue.fail(lease, "SYNTHETIC_TRANSIENT", retry=True)
        async with database.sessions() as session, session.begin():
            await session.execute(
                update(SearchTask)
                .where(SearchTask.id == lease.task_id)
                .values(next_retry_at=utcnow() - timedelta(seconds=1))
            )
    async with database.sessions() as session:
        view = await ExecutionService(session).get(user, identifier)
        assert view.status == "FAILED" and view.attempt == 3


async def test_api_scope_sse_and_unsupported_mode(database: Runtime) -> None:
    user, profile = await prepare(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            assert (await client.get("/api/search/executions")).status_code == 401
            assert (
                await client.post(
                    "/api/auth/login",
                    json={"email": "queue@example.test", "password": "fixture-password-for-queue"},
                )
            ).status_code == 200
            created = await client.post("/api/search/executions", json={"profile_id": str(profile)})
            assert created.status_code == 202
            identifier = created.json()["id"]
            await SearchQueue(database).run_once()
            event = await client.get(f"/api/search/executions/{identifier}/events")
            assert (
                event.status_code == 200
                and "event: progress" in event.text
                and '"status":"SUCCEEDED"' in event.text
            )
            assert (
                await client.get(f"/api/search/executions/{identifier}/results?sort=visa")
            ).json()["total"] == 2
            assert (await client.get(f"/api/search/executions/{uuid4()}/events")).status_code == 404
            assert (await client.get("/api/search/dashboard")).json()["imported_count"] == 2
            assert (
                await client.get(f"/api/search/executions/{identifier}/results?sort=invalid")
            ).status_code == 422
            async with database.sessions() as session:
                await SearchService(session).update(
                    user,
                    profile,
                    ProfileInput(
                        name="CV unavailable",
                        criteria=SearchCriteria(mode="CV", source_ids=[SOURCE]),
                    ),
                )
            assert (
                await client.post("/api/search/executions", json={"profile_id": str(profile)})
            ).status_code == 409
    finally:
        await app.state.runtime.engine.dispose()


async def test_timeout_and_pending_cancellation(
    database: Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, profile = await prepare(database)
    identifier = await request(database, user, profile)
    async with database.sessions() as session:
        await ExecutionService(session).cancel(user, identifier)
    queue = SearchQueue(database)
    assert not await queue.run_once()
    async with database.sessions() as session:
        assert (await ExecutionService(session).get(user, identifier)).status == "CANCELLED"
    identifier = await request(database, user, profile)

    async def timeout(*args: object) -> None:
        raise TimeoutError

    monkeypatch.setattr(queue, "_process", timeout)
    await queue.run_once()
    async with database.sessions() as session:
        assert (await ExecutionService(session).get(user, identifier)).status == "TIMED_OUT"
