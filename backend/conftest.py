import asyncio
import base64
import os
import secrets
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.db import Runtime, make_runtime
from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:fixture-only@127.0.0.1:1/jobhunter_test",
        jwt_secret=secrets.token_urlsafe(64),
        cv_encryption_key=base64.b64encode(secrets.token_bytes(32)).decode(),
        environment="test",
    )


@pytest.fixture
async def database(settings: Settings) -> AsyncIterator[Runtime]:
    env_path = Path(os.environ.get("JOBHUNTER_TEST_ENV", ".env.test"))
    values = await asyncio.to_thread(dotenv_values, env_path)
    url = os.environ.get("TEST_DATABASE_URL") or values.get("DATABASE_URL")
    if not url:
        pytest.skip("Dedicated PostgreSQL not configured: backend/.env.test or TEST_DATABASE_URL")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        pytest.fail(
            "Integration database name must end in _test; refusing to modify other databases"
        )
    schema = "test_" + uuid4().hex
    data = settings.model_dump()
    data.update(database_url=url, database_schema="public")
    admin_settings = Settings(_env_file=None, **data)
    admin = make_runtime(admin_settings)
    created = False
    runtime = None
    try:
        try:
            async with admin.engine.begin() as connection:
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        except Exception as exc:
            pytest.fail(
                f"Dedicated PostgreSQL unavailable ({type(exc).__name__}); credentials hidden"
            )
        data["database_schema"] = schema
        scoped_settings = Settings(_env_file=None, **data)
        env = os.environ.copy()
        env.update(
            DATABASE_URL=url,
            DATABASE_SCHEMA=schema,
            JWT_SECRET=scoped_settings.jwt_secret.get_secret_value(),
            CV_ENCRYPTION_KEY=scoped_settings.cv_encryption_key.get_secret_value(),
            ALLOWED_ORIGINS='["https://localhost:8443"]',
            ENVIRONMENT="test",
        )
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            pytest.fail("Migration failed on dedicated PostgreSQL; credentials hidden")
        runtime = make_runtime(scoped_settings)
        yield runtime
    finally:
        if runtime:
            await runtime.engine.dispose()
        if created:
            # Drop ONLY the random schema created by this fixture, never an existing schema.
            async with admin.engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.engine.dispose()
