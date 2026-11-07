import asyncio
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import inspect, select, text

from app.core.db import Runtime
from app.core.errors import AppError
from app.main import create_app
from app.modules.auth import AuthService
from app.modules.auth.models import AppUser, AuthSession, RefreshToken
from app.modules.auth.service import Tokens
from app.shared.clock import utcnow
from app.worker import run_worker

pytestmark = pytest.mark.integration
PASSWORD = "fixture-owner-password-long"
EMAIL = "owner@example.test"
ORIGIN = {"Origin": "https://localhost:8443"}


async def create_owner(database: Runtime) -> None:
    async with database.sessions() as session:
        await AuthService(session, database.settings).setup_owner(EMAIL, PASSWORD)


async def login(database: Runtime) -> Tokens:
    async with database.sessions() as session:
        return await AuthService(session, database.settings).login(
            EMAIL, PASSWORD, "test-client-key"
        )


async def test_migration_and_owner_setup_lock(database: Runtime) -> None:
    async with database.engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert {"app_users", "auth_sessions", "refresh_tokens", "login_buckets"} <= set(tables)
    assert revision == "0001_auth"
    await create_owner(database)
    async with database.sessions() as session:
        with pytest.raises(AppError, match="already exists"):
            await AuthService(session, database.settings).setup_owner(
                "second@example.test", PASSWORD
            )
    async with database.sessions() as session:
        users = (await session.scalars(select(AppUser))).all()
        assert len(users) == 1
        assert users[0].password_hash.startswith("$argon2id$")
        assert PASSWORD not in users[0].password_hash


async def test_concurrent_setup_creates_exactly_one_owner(database: Runtime) -> None:
    async def setup(email: str) -> str:
        async with database.sessions() as session:
            try:
                await AuthService(session, database.settings).setup_owner(email, PASSWORD)
                return "created"
            except AppError as exc:
                return exc.code

    outcomes = await asyncio.gather(setup(EMAIL), setup("other@example.test"))
    assert sorted(outcomes) == ["SETUP_LOCKED", "created"]


async def test_failed_logins_commit_and_trigger_lockout(database: Runtime) -> None:
    await create_owner(database)
    for _ in range(database.settings.login_max_failures):
        async with database.sessions() as session:
            with pytest.raises(AppError) as error:
                await AuthService(session, database.settings).login(EMAIL, "wrong", "fixed-client")
            assert error.value.status == 401
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await AuthService(session, database.settings).login(EMAIL, PASSWORD, "other-client")
        assert error.value.status == 429


async def test_unknown_account_is_rate_limited(database: Runtime) -> None:
    for _ in range(database.settings.login_max_failures):
        async with database.sessions() as session:
            with pytest.raises(AppError):
                await AuthService(session, database.settings).login(
                    "unknown@example.test", "bad", "ip"
                )
    async with database.sessions() as session:
        with pytest.raises(AppError) as error:
            await AuthService(session, database.settings).login("unknown@example.test", "bad", "ip")
        assert error.value.status == 429


async def test_rotation_reuse_revokes_access_and_refresh(database: Runtime) -> None:
    await create_owner(database)
    first = await login(database)
    async with database.sessions() as session:
        second = await AuthService(session, database.settings).rotate(first.refresh)
    assert second.refresh != first.refresh
    async with database.sessions() as session:
        token_rows = (await session.scalars(select(RefreshToken))).all()
        assert len(token_rows) == 2
        assert all(row.token_hash not in {first.refresh, second.refresh} for row in token_rows)
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await AuthService(session, database.settings).rotate(first.refresh)
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await AuthService(session, database.settings).current_owner(second.access)
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await AuthService(session, database.settings).rotate(second.refresh)


async def test_concurrent_refresh_detects_reuse(database: Runtime) -> None:
    await create_owner(database)
    tokens = await login(database)

    async def rotate() -> Tokens | None:
        async with database.sessions() as session:
            try:
                return await AuthService(session, database.settings).rotate(tokens.refresh)
            except AppError:
                return None

    outcomes = await asyncio.gather(rotate(), rotate())
    assert sum(outcome is not None for outcome in outcomes) == 1
    async with database.sessions() as session:
        family = await session.scalar(select(AuthSession))
        assert family is not None
        assert family.revoked_at is not None


async def test_expired_session_cannot_refresh_or_access(database: Runtime) -> None:
    await create_owner(database)
    tokens = await login(database)
    async with database.sessions() as session:
        family = await session.scalar(select(AuthSession))
        assert family is not None
        family.expires_at = utcnow() - timedelta(seconds=1)
        await session.commit()
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await AuthService(session, database.settings).rotate(tokens.refresh)
    async with database.sessions() as session:
        with pytest.raises(AppError):
            await AuthService(session, database.settings).current_owner(tokens.access)


async def test_full_http_login_rotation_logout(database: Runtime) -> None:
    await create_owner(database)
    app = create_app(database.settings)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
            headers=ORIGIN,
        ) as client:
            response = await client.post(
                "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
            )
            assert response.status_code == 200
            assert "password" not in response.text and "access" not in response.text
            for cookie in response.headers.get_list("set-cookie"):
                assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
            assert (await client.get("/api/account")).json()["email"] == EMAIL
            assert (await client.post("/api/auth/refresh")).status_code == 200
            old_access = client.cookies.get("__Host-jh_access")
            assert (await client.post("/api/auth/logout")).status_code == 204
            assert not list(client.cookies)
            assert (await client.get("/api/account")).status_code == 401
            replay = await client.get(
                "/api/account", headers={"Cookie": f"__Host-jh_access={old_access}"}
            )
            assert replay.status_code == 401
            assert (await client.get("/health")).status_code == 200
    finally:
        await app.state.runtime.engine.dispose()


async def test_api_lifespan_and_worker_database_probe(database: Runtime) -> None:
    app = create_app(database.settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://localhost:8443",
        ) as client:
            assert (await client.get("/health")).status_code == 200
    await run_worker(database, asyncio.Event(), once=True)
