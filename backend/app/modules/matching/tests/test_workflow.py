from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from app.core.db import Runtime
from app.core.errors import AppError
from app.modules.cv import CvBlob, CvService
from app.modules.listings import ListingService
from app.modules.listings.schemas import ImportJob, ImportRequest
from app.modules.matching import MatchingService
from app.modules.matching.models import JobMatch, MatchingRun
from app.modules.matching.schemas import MatchingSnapshot, MatchJobInput
from app.modules.matching.service import ComputedMatch
from app.modules.profile import ProfileService
from app.modules.profile.schemas import CandidateInput
from app.modules.search.execution_schemas import ExecutionInput
from app.modules.search.executions import ExecutionService
from app.modules.search.models import SearchTask
from app.modules.search.queue import SearchQueue
from app.modules.search.tests.test_queue import SOURCE, lookup, prepare
from app.modules.sources import SourceService
from app.shared.document import DocumentInspection, DocumentPage
from tests.document_fixtures import pdf_fixture

pytestmark = pytest.mark.integration


async def candidate(database: Runtime, owner: UUID) -> UUID:
    async def inspect(content: bytes, filename: str, content_type: str) -> DocumentInspection:
        return DocumentInspection(
            status="TEXT",
            kind="PDF",
            pages=[
                DocumentPage(number=1, text="SYNTHETIC_PRIVATE_MATCHING_MARKER\nSkills\nPython")
            ],
        )

    async with database.sessions() as session:
        cv = await CvService(session, database.settings).upload(
            owner, CvBlob("synthetic.pdf", "application/pdf", pdf_fixture()), inspect
        )
    async with database.sessions() as session:
        draft = await ProfileService(session, database.settings).generate(owner, cv.id, False)
    async with database.sessions() as session:
        await ProfileService(session, database.settings).validate(owner, draft.id)
    async with database.sessions() as session:
        await ProfileService(session, database.settings).activate(owner, draft.id)
    return cv.document_id


async def launch(database: Runtime, owner: UUID, profile: UUID, source: UUID | None = None) -> UUID:
    options = ExecutionInput(
        profile_id=profile,
        matching_preview=True,
        scope="MATCHING_ONLY" if source else "IMPORTED_OFFERS",
        source_execution_id=source,
    )
    async with database.sessions() as session:
        return (
            await ExecutionService(session, settings=database.settings).request(
                owner, profile, lookup(database), options
            )
        ).id


async def test_preview_rescore_cache_ownership_privacy_and_delete(
    database: Runtime, tmp_path: Path
) -> None:
    database.settings.cv_storage_path = tmp_path / "vault"
    owner, profile = await prepare(database)
    document = await candidate(database, owner)
    first = await launch(database, owner, profile)
    assert await SearchQueue(database).run_once()
    async with database.sessions() as session:
        view = await ExecutionService(session).get(owner, first)
        assert view.status == "SUCCEEDED" and view.matching and view.matching.cursor == 2
        assert view.counts["matched"] == 2
        serialized = view.model_dump_json()
        assert "Python" not in serialized and "SYNTHETIC_PRIVATE" not in serialized
        page = await MatchingService(session, database.settings).page(owner, first, [], 0, 20)
        assert len(page.items) == 2 and all(item.preview.provisional for item in page.items)
        raw = (await session.scalars(select(JobMatch))).all()
        assert all(b"Python" not in row.private_payload for row in raw)
        with pytest.raises(AppError) as error:
            await MatchingService(session, database.settings).page(uuid4(), first, [], 0, 20)
        assert error.value.status == 404
    second = await launch(database, owner, profile, first)
    assert await SearchQueue(database).run_once()
    async with database.sessions() as session:
        view = await ExecutionService(session).get(owner, second)
        assert view.scope == "MATCHING_ONLY" and view.status == "SUCCEEDED"
        assert view.matching and view.matching.cache_hits == 2
        assert view.counts["scanned"] == 0
        assert (await ExecutionService(session).get(owner, first)).counts["matched"] == 2
    async with database.sessions() as session:
        await CvService(session, database.settings).delete_document(owner, document)
    async with database.sessions() as session:
        assert not (await session.scalars(select(JobMatch))).all()
        assert not (await session.scalars(select(MatchingRun))).all()
        assert (await ExecutionService(session).results(owner, first, 20, 0)).total == 2


async def test_readiness_cancel_and_active_candidate_change(
    database: Runtime, tmp_path: Path
) -> None:
    database.settings.cv_storage_path = tmp_path / "vault"
    owner, profile = await prepare(database)
    async with database.sessions() as session, session.begin():
        assert not (await MatchingService(session, database.settings).capabilities(owner))["ready"]
    with pytest.raises(AppError):
        await launch(database, owner, profile)
    await candidate(database, owner)
    first = await launch(database, owner, profile)
    async with database.sessions() as session:
        await ExecutionService(session).cancel(owner, first)
    assert not await SearchQueue(database).run_once()
    async with database.sessions() as session:
        view = await ExecutionService(session).get(owner, first)
        assert view.status == "CANCELLED" and view.matching and view.matching.status == "CANCELLED"
    second = await launch(database, owner, profile)
    async with database.sessions() as session:
        active = await ProfileService(session, database.settings).validated_active(owner)
    async with database.sessions() as session:
        edited = await ProfileService(session, database.settings).edit(
            owner,
            active.id,
            CandidateInput(
                fields=active.data.fields.model_copy(update={"professional_title": "Changed"})
            ),
        )
    async with database.sessions() as session:
        await ProfileService(session, database.settings).validate(owner, edited.id)
    async with database.sessions() as session:
        await ProfileService(session, database.settings).activate(owner, edited.id)
    assert await SearchQueue(database).run_once()
    async with database.sessions() as session:
        view = await ExecutionService(session).get(owner, second)
        assert view.status == "FAILED" and view.reason == "PROFILE_CHANGED"
        assert not (await session.scalars(select(JobMatch))).all()


async def test_retry_retains_matching_cursor_without_duplicate_matches(
    database: Runtime, tmp_path: Path
) -> None:
    database.settings.cv_storage_path = tmp_path / "vault"
    owner, profile = await prepare(database)
    await candidate(database, owner)
    first = await launch(database, owner, profile)
    queue = SearchQueue(database)
    lease = await queue.claim()
    assert lease
    # Persist a complete matching batch, simulate process death before terminalization.
    async with database.sessions() as session:
        scan = await ExecutionService(session).get(owner, first)
    criteria, workset, cursor, _ = await queue._load(lease)

    async def crash(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated transaction interruption")

    from unittest.mock import patch

    with patch.object(MatchingService, "finish", crash), pytest.raises(RuntimeError):
        await queue._process(lease, criteria, workset, cursor)
    async with database.sessions() as session:
        assert not (await session.scalars(select(JobMatch))).all()
    assert scan.status == "RUNNING"
    from datetime import timedelta

    from app.shared.clock import utcnow

    async with database.sessions() as session, session.begin():
        await session.execute(
            update(SearchTask)
            .where(SearchTask.execution_id == first)
            .values(heartbeat_at=utcnow() - timedelta(minutes=3))
        )
    assert await queue.run_once()
    async with database.sessions() as session:
        assert len((await session.scalars(select(JobMatch))).all()) == 2
        assert (await ExecutionService(session).get(owner, first)).status == "SUCCEEDED"


@pytest.mark.parametrize("outcome", ["resume", "cancel", "delete"])
async def test_durable_matching_batches_after_crash(
    database: Runtime, tmp_path: Path, outcome: str
) -> None:
    from datetime import timedelta
    from unittest.mock import patch

    from app.shared.clock import utcnow

    database.settings.cv_storage_path = tmp_path / "vault"
    owner, profile = await prepare(database)
    document = await candidate(database, owner)
    async with database.sessions() as session:
        source = await SourceService(session).resolve(owner, SOURCE)
    async with database.sessions() as session:
        await ListingService(session).import_jobs(
            owner,
            source,
            ImportRequest(
                source_id=SOURCE,
                confirm=True,
                jobs=[
                    ImportJob(
                        original_url=f"https://example.test/checkpoint/{index}",
                        title=f"Distinct synthetic posting {index}",
                    )
                    for index in range(20)
                ],
            ),
        )
    identifier = await launch(database, owner, profile)
    queue = SearchQueue(database)
    lease = await queue.claim()
    assert lease
    criteria, workset, cursor, _ = await queue._load(lease)
    compute, calls = MatchingService.compute, 0

    def interrupted(snapshot: MatchingSnapshot, jobs: list[MatchJobInput]) -> list[ComputedMatch]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic process death after checkpoint")
        return compute(snapshot, jobs)

    with patch.object(MatchingService, "compute", interrupted), pytest.raises(RuntimeError):
        await queue._process(lease, criteria, workset, cursor)
    async with database.sessions() as session:
        run = await MatchingService(session, database.settings).metadata(owner, identifier)
        assert run and run.cursor == 20
        assert len((await session.scalars(select(JobMatch))).all()) == 20
    if outcome == "cancel":
        async with database.sessions() as session:
            await ExecutionService(session).cancel(owner, identifier)
    elif outcome == "delete":
        async with database.sessions() as session:
            await CvService(session, database.settings).delete_document(owner, document)
    async with database.sessions() as session, session.begin():
        await session.execute(
            update(SearchTask)
            .where(SearchTask.execution_id == identifier)
            .values(heartbeat_at=utcnow() - timedelta(minutes=3))
        )
    await queue.run_once()
    async with database.sessions() as session:
        view = await ExecutionService(session).get(owner, identifier)
        rows = (await session.scalars(select(JobMatch))).all()
        if outcome == "resume":
            assert view.status == "SUCCEEDED" and len(rows) == 22
            assert view.matching and view.matching.cursor == 22
        elif outcome == "cancel":
            assert view.status == "CANCELLED" and len(rows) == 20
        else:
            assert view.status == "FAILED" and view.reason == "MATCHING_INPUT_UNAVAILABLE"
            assert not rows
