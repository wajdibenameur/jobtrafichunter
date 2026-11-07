import logging
from uuid import UUID

import httpx
import pytest

from app.core.settings import Settings
from app.main import create_app


@pytest.fixture
async def client(settings: Settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://localhost:8443",
    ) as client:
        yield client
    await app.state.runtime.engine.dispose()


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/account"])
async def test_unauthenticated_rejected(client: httpx.AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null"])
async def test_mutation_requires_trusted_origin(
    client: httpx.AsyncClient, origin: str | None
) -> None:
    headers = {"Origin": origin} if origin else {}
    response = await client.post("/api/auth/refresh", headers=headers)
    assert response.status_code == 403


async def test_invalid_body_never_echoes_password(client: httpx.AsyncClient, caplog) -> None:
    secret = "private-fixture-password-do-not-echo"
    response = await client.post(
        "/api/auth/login",
        json={"email": "", "password": secret},
        headers={"Origin": "https://localhost:8443"},
    )
    assert response.status_code == 422
    assert secret not in response.text and secret not in caplog.text


async def test_security_headers_and_correlation_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/auth/me", headers={"X-Correlation-ID": "untrusted\tvalue"})
    assert UUID(response.headers["X-Correlation-ID"])
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


async def test_health_distinguishes_database_unavailable(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
    assert "fixture-only" not in response.text


async def test_openapi_describes_auth_without_setup_endpoint(client: httpx.AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    assert "/api/auth/login" in paths and "/api/account" in paths
    assert not any("setup" in path for path in paths)


def test_json_logging_has_no_exception_payload() -> None:
    from app.core.logging import JsonFormatter

    record = logging.LogRecord("test", logging.ERROR, "", 1, "request_failed", (), None)
    assert '"event": "request_failed"' in JsonFormatter().format(record)


async def test_oversized_and_chunked_auth_body_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        content=b"x" * 17000,
        headers={"Origin": "https://localhost:8443"},
    )
    assert response.status_code == 413
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    async def chunks():
        yield b"x" * 9000
        yield b"x" * 9000

    response = await client.post(
        "/api/auth/login",
        content=chunks(),
        headers={"Origin": "https://localhost:8443"},
    )
    assert response.status_code == 413


async def test_docs_csp_allows_only_the_generated_initializer(client: httpx.AsyncClient) -> None:
    import base64
    import hashlib
    import re

    response = await client.get("/docs")
    assert response.status_code == 200
    scripts = re.findall(r"<script>(.*?)</script>", response.text, flags=re.DOTALL)
    assert scripts
    policy = response.headers["Content-Security-Policy"]
    for script in scripts:
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in policy
