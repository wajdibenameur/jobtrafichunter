from uuid import uuid4

import httpx
import pytest

from app.core.db import Runtime
from app.core.settings import Settings
from app.main import create_app
from app.modules.auth import AuthService


async def test_matching_routes_require_authentication(settings: Settings) -> None:
    app = create_app(settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://localhost:8443"
        ) as client:
            for path in [
                "/api/matching/capabilities",
                "/api/matching/policies",
                f"/api/matching/executions/{uuid4()}",
            ]:
                assert (await client.get(path)).status_code == 401
            response = await client.post(
                "/api/matching/policies", json={}, headers={"Origin": "https://localhost:8443"}
            )
            assert response.status_code == 401
    finally:
        await app.state.runtime.engine.dispose()


@pytest.mark.integration
async def test_matching_api_readiness_policy_validation_origin_and_sanitization(
    database: Runtime,
) -> None:
    async with database.sessions() as session:
        await AuthService(session, database.settings).setup_owner(
            "matching-api@example.test", "fixture-password-matching-api"
        )
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://localhost:8443"
        ) as client:
            origin = {"Origin": "https://localhost:8443"}
            login = await client.post(
                "/api/auth/login",
                headers=origin,
                json={
                    "email": "matching-api@example.test",
                    "password": "fixture-password-matching-api",
                },
            )
            assert login.status_code == 200
            response = await client.get("/api/matching/capabilities")
            assert response.status_code == 200 and not response.json()["ready"]
            assert response.json()["calibration_status"] == "UNVALIDATED"
            assert (await client.post("/api/matching/policies", json={})).status_code == 403
            invalid = await client.post(
                "/api/matching/policies",
                headers=origin,
                json={"weights": {"SYNTHETIC_PRIVATE_FIELD": 101}},
            )
            assert invalid.status_code == 422 and "SYNTHETIC_PRIVATE_FIELD" not in invalid.text
            saved = await client.post("/api/matching/policies", headers=origin, json={})
            assert saved.status_code == 201 and saved.json()["version"] == 1
            same = await client.post("/api/matching/policies", headers=origin, json={})
            assert same.json()["id"] == saved.json()["id"]
            missing = await client.get(f"/api/matching/executions/{uuid4()}")
            assert missing.status_code == 404
    finally:
        await app.state.runtime.engine.dispose()
