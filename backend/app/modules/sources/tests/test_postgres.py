from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.sources.models import JobSource
from app.modules.sources.schemas import SearchLinkRequest, SourceCreate, SourcePatch, SourceSettings
from app.modules.sources.service import SourceService

pytestmark = pytest.mark.integration


async def owner_id(database: Runtime) -> UUID:
    async with database.sessions() as session:
        return (
            await AuthService(session, database.settings).setup_owner(
                "source-owner@example.test", "fixture-password-long"
            )
        ).id


async def test_seeded_manual_sources_and_persistent_preferences(database: Runtime) -> None:
    user = await owner_id(database)
    async with database.sessions() as session:
        rows = await SourceService(session).list(user)
    assert {row.slug for row in rows} == {"linkedin", "indeed", "keejob", "tanitjobs"}
    assert all(not row.enabled and not row.automation_eligible for row in rows)
    source = next(row for row in rows if row.slug == "keejob")
    async with database.sessions() as session:
        updated = await SourceService(session).patch(
            user,
            source.id,
            SourcePatch(enabled=True, settings=SourceSettings(keywords="Python", location="Tunis")),
        )
    assert updated.enabled and updated.settings.location == "Tunis"
    async with database.sessions() as session:
        restored = await SourceService(session).list(user)
    assert next(row for row in restored if row.id == source.id).enabled


async def test_unverified_api_cannot_be_enabled_even_by_direct_patch(database: Runtime) -> None:
    user = await owner_id(database)
    async with database.sessions() as session:
        source = (
            await session.scalars(select(JobSource).where(JobSource.slug == "linkedin"))
        ).one()
        source.integration_type = "API"
        source.legal_status = "UNVERIFIED"
        source_id = source.id
        await session.commit()
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await SourceService(session).patch(user, source_id, SourcePatch(enabled=True))
        assert error.value.code == "AUTOMATION_NOT_PERMITTED"


async def test_custom_source_is_owner_scoped(database: Runtime) -> None:
    user = await owner_id(database)
    async with database.sessions() as session:
        created = await SourceService(session).create(
            user, SourceCreate(name="Career page", homepage="https://careers.example.test/jobs")
        )
    async with database.sessions() as session:
        service = SourceService(session)
        assert created.id not in {row.id for row in await service.list(uuid4())}
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await SourceService(session).resolve(uuid4(), created.id)
    async with database.sessions() as session:
        await SourceService(session).delete(user, created.id)


async def test_provider_search_links_preserve_encoded_criteria(database: Runtime) -> None:
    user = await owner_id(database)
    async with database.sessions() as session:
        service = SourceService(session)
        sources = await service.list(user)
        links = {
            source.slug: await service.search_link(
                user, source.id, SearchLinkRequest(keywords="Java & Angular", location="Tunis")
            )
            for source in sources
        }
    assert parse_qs(urlsplit(links["linkedin"].url).query)["keywords"] == ["Java & Angular"]
    assert parse_qs(urlsplit(links["indeed"].url).query)["l"] == ["Tunis"]
    assert parse_qs(urlsplit(links["tanitjobs"].url).query)["keywords[all_words]"] == [
        "Java & Angular"
    ]
    assert "Tunis" in parse_qs(urlsplit(links["keejob"].url).query)["keywords"][0]


async def test_http_auth_and_source_crud(database: Runtime) -> None:
    await owner_id(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            assert (await client.get("/api/sources")).status_code == 401
            login = await client.post(
                "/api/auth/login",
                json={"email": "source-owner@example.test", "password": "fixture-password-long"},
            )
            assert login.status_code == 200
            sources = (await client.get("/api/sources")).json()
            updated = await client.patch(f"/api/sources/{sources[0]['id']}", json={"enabled": True})
            assert updated.status_code == 200 and updated.json()["enabled"] is True
            forbidden = await client.patch(
                f"/api/sources/{sources[0]['id']}", json={"legal_status": "PERMITTED"}
            )
            assert forbidden.status_code == 422
    finally:
        await app.state.runtime.engine.dispose()
