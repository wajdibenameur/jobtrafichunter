from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.search.schemas import ProfileInput, SearchCriteria
from app.modules.search.service import SearchService


@pytest.mark.parametrize(
    "values",
    [
        {"max_years": -1},
        {"publication_days": 2},
        {"mode": "fake"},
        {"include_keywords": [" "]},
        {"cities": ["bad\x00text"]},
        {"include_keywords": ["x" * 101]},
        {"countries": [str(i) for i in range(101)]},
    ],
)
def test_invalid_criteria_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SearchCriteria.model_validate(values)


def test_defaults_and_distinct_values() -> None:
    criteria = SearchCriteria(include_keywords=["Python", "Python"])
    assert criteria.max_years == 3 and criteria.include_keywords == ["Python"]
    assert criteria.unknown_policy == "include" and criteria.mode == "MANUAL"


async def owner(database: Runtime) -> UUID:
    async with database.sessions() as session:
        return (
            await AuthService(session, database.settings).setup_owner(
                "search@example.test", "fixture-password-for-search"
            )
        ).id


@pytest.mark.integration
async def test_profile_crud_duplicate_scope_and_explicit_examples(database: Runtime) -> None:
    user = await owner(database)
    async with database.sessions() as session:
        first = await SearchService(session).create(user, ProfileInput(name="My profile"))
    async with database.sessions() as session:
        updated = await SearchService(session).update(
            user,
            first.id,
            ProfileInput(
                name="Tunisia", criteria=SearchCriteria(countries=["Tunisia"], max_years=2)
            ),
        )
    assert updated.criteria.max_years == 2
    async with database.sessions() as session:
        copied = await SearchService(session).duplicate(user, first.id, "Copy")
    assert copied.id != first.id and copied.criteria == updated.criteria
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await SearchService(session).get(uuid4(), first.id)
        assert error.value.status == 404
    async with database.sessions() as session:
        await SearchService(session).delete(user, first.id)
    async with database.sessions() as session:
        rows = await SearchService(session).examples(user)
    assert len(rows) == 4
    async with database.sessions() as session:
        assert len(await SearchService(session).examples(user)) == 4
    async with database.sessions() as session:
        assert (await SearchService(session).get(user, copied.id)).name == "Copy"


@pytest.mark.integration
async def test_profile_api_auth_validation_and_source_scope(database: Runtime) -> None:
    await owner(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers={"Origin": "https://localhost:8443"},
        ) as client:
            assert (await client.get("/api/search/profiles")).status_code == 401
            assert (
                await client.post(
                    "/api/auth/login",
                    json={
                        "email": "search@example.test",
                        "password": "fixture-password-for-search",
                    },
                )
            ).status_code == 200
            assert (
                await client.post("/api/search/profiles", json={"name": " ", "criteria": {}})
            ).status_code == 422
            assert (
                await client.post(
                    "/api/search/profiles",
                    json={"name": "No source", "criteria": {"source_ids": [str(uuid4())]}},
                )
            ).status_code == 404
            created = await client.post("/api/search/profiles", json={"name": "Manual"})
            assert created.status_code == 201
            identifier = created.json()["id"]
            assert (await client.get(f"/api/search/profiles/{identifier}")).status_code == 200
            assert (await client.delete(f"/api/search/profiles/{identifier}")).status_code == 204
            assert (await client.get(f"/api/search/profiles/{identifier}")).status_code == 404
    finally:
        await app.state.runtime.engine.dispose()
