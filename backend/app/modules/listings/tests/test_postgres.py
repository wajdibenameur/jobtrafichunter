import asyncio
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import inspect

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.listings.schemas import ImportJob, ImportRequest, ImportResult
from app.modules.listings.service import ListingService
from app.modules.sources import SourceService
from app.shared.source_reference import SourceReference

pytestmark = pytest.mark.integration
SOURCE_ID = UUID("10000000-0000-4000-8000-000000000001")
PASSWORD = "fixture-password-for-imports"


async def setup(database: Runtime) -> tuple[UUID, SourceReference]:
    async with database.sessions() as session:
        owner = await AuthService(session, database.settings).setup_owner(
            "import@example.test", PASSWORD
        )
    async with database.sessions() as session:
        source = await SourceService(session).resolve(owner.id, SOURCE_ID)
    return owner.id, source


async def test_migration_idempotence_and_novelty(database: Runtime) -> None:
    user, source = await setup(database)
    body = ImportRequest(
        source_id=source.id,
        confirm=True,
        jobs=[
            ImportJob(
                original_url="https://www.linkedin.com/jobs/view/123?utm_source=fixture",
                title="Python",
            )
        ],
    )
    async with database.sessions() as session:
        first = await ListingService(session).import_jobs(user, source, body)
    body.jobs[0].original_url = "https://www.linkedin.com/jobs/view/123?trk=other"
    async with database.sessions() as session:
        repeated = await ListingService(session).import_jobs(user, source, body)
    assert first.created_count == 1 and repeated.created_count == 0 and repeated.existing_count == 1
    assert first.listings[0].id == repeated.listings[0].id
    assert first.listings[0].first_seen_at == repeated.listings[0].first_seen_at
    assert (
        first.listings[0].published_at is None and first.listings[0].visa_status == "NOT_SPECIFIED"
    )
    assert first.listings[0].original_url.endswith("utm_source=fixture")
    async with database.engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
    assert "listing_import_records" in tables


async def test_url_only_then_enrichment_preserves_known_data(database: Runtime) -> None:
    user, source = await setup(database)

    async def submit(job: ImportJob) -> ImportResult:
        async with database.sessions() as session:
            return await ListingService(session).import_jobs(
                user, source, ImportRequest(source_id=source.id, confirm=True, jobs=[job])
            )

    job_url = "https://example.test/jobs/123"
    first = await submit(ImportJob(original_url=job_url))
    assert first.listings[0].title is None and "description" in first.listings[0].missing_fields
    enriched = await submit(
        ImportJob(original_url=job_url, title="Backend", description="Actual pasted description")
    )
    repeated = await submit(ImportJob(original_url=job_url))
    assert repeated.listings[0].description == enriched.listings[0].description
    assert repeated.listings[0].first_seen_at == first.listings[0].first_seen_at
    async with database.sessions() as session:
        assert (await ListingService(session).page(uuid4(), 20, 0)).total == 0


async def test_concurrent_imports_create_one_listing(database: Runtime) -> None:
    user, source = await setup(database)
    body = ImportRequest(
        source_id=source.id,
        confirm=True,
        jobs=[ImportJob(original_url="https://example.test/concurrent", title="Job")],
    )

    async def submit() -> ImportResult:
        async with database.sessions() as session:
            return await ListingService(session).import_jobs(user, source, body)

    results = await asyncio.gather(submit(), submit())
    assert sum(result.created_count for result in results) == 1
    async with database.sessions() as session:
        assert (await ListingService(session).page(user, 20, 0)).total == 1


async def test_import_endpoints_auth_preview_and_confirmation(database: Runtime) -> None:
    await setup(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            assert (await client.get("/api/jobs")).status_code == 401
            login = await client.post(
                "/api/auth/login", json={"email": "import@example.test", "password": PASSWORD}
            )
            assert login.status_code == 200
            preview = await client.post(
                "/api/jobs/import/preview",
                json={
                    "source_id": str(SOURCE_ID),
                    "csv_text": 'url,title,description\nhttps://example.test/1,Python,"'
                    + "x" * 20000
                    + '"\n',
                },
            )
            assert preview.status_code == 200 and preview.json()["valid_count"] == 1
            assert "visa_status" not in preview.json()["rows"][0]["job"]
            assert "mandatory_skills" not in preview.json()["rows"][0]["job"]
            assert (await client.get("/api/jobs")).json()["total"] == 0
            payload: dict[str, object] = {
                "source_id": str(SOURCE_ID),
                "jobs": [preview.json()["rows"][0]["job"]],
            }
            assert (await client.post("/api/jobs/import", json=payload)).status_code == 422
            payload["confirm"] = True
            imported = await client.post("/api/jobs/import", json=payload)
            assert imported.status_code == 201 and imported.json()["created_count"] == 1
            assert (await client.get("/api/jobs")).json()["total"] == 1
            assert (
                await client.post(
                    "/api/jobs/import",
                    json={
                        "source_id": str(SOURCE_ID),
                        "confirm": True,
                        "jobs": [
                            {
                                "original_url": "https://example.test/1",
                                "visa_status": "CONFIRMED",
                                "visa_evidence": "Synthetic fixture evidence",
                            }
                        ],
                    },
                )
            ).status_code == 201
            assert (await client.post("/api/jobs/import", json=payload)).status_code == 201
            assert (await client.get("/api/jobs")).json()["items"][0]["visa_status"] == "CONFIRMED"
            payload["source_id"] = str(uuid4())
            assert (await client.post("/api/jobs/import", json=payload)).status_code == 404
            too_large = await client.post(
                "/api/jobs/import/preview", content=b"x" * (1024 * 1024 + 1)
            )
            assert too_large.status_code == 413
    finally:
        await app.state.runtime.engine.dispose()


async def test_conflicting_identifiers_roll_back_entire_batch(database: Runtime) -> None:
    user, source = await setup(database)
    async with database.sessions() as session:
        await ListingService(session).import_jobs(
            user,
            source,
            ImportRequest(
                source_id=source.id,
                confirm=True,
                jobs=[
                    ImportJob(original_url="https://example.test/a", source_job_id="a"),
                    ImportJob(original_url="https://example.test/b", source_job_id="b"),
                ],
            ),
        )
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await ListingService(session).import_jobs(
                user,
                source,
                ImportRequest(
                    source_id=source.id,
                    confirm=True,
                    jobs=[
                        ImportJob(original_url="https://example.test/new"),
                        ImportJob(original_url="https://example.test/a", source_job_id="b"),
                    ],
                ),
            )
        assert error.value.code == "IMPORT_CONFLICT"
    async with database.sessions() as session:
        page = await ListingService(session).page(user, 20, 0)
        assert page.total == 2
        assert all(item.original_url != "https://example.test/new" for item in page.items)
