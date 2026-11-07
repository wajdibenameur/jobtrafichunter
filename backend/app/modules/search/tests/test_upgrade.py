import asyncio
import os
import subprocess
import sys

import pytest

from app.core.db import Runtime
from app.modules.listings import ListingCatalog, ListingService
from app.modules.search.tests.test_queue import SOURCE, prepare


@pytest.mark.integration
async def test_phase_two_imports_backfilled_without_changing_originals(database: Runtime) -> None:
    user, _ = await prepare(database)
    async with database.sessions() as session:
        original = await ListingService(session).page(user, 20, 0)
    settings = database.settings
    assert settings.database_schema.startswith("test_")
    env = os.environ.copy()
    env.update(
        DATABASE_URL=settings.database_url.get_secret_value(),
        DATABASE_SCHEMA=settings.database_schema,
        JWT_SECRET=settings.jwt_secret.get_secret_value(),
        CV_ENCRYPTION_KEY=settings.cv_encryption_key.get_secret_value(),
        ENVIRONMENT="test",
        ALLOWED_ORIGINS='["https://localhost:8443"]',
    )
    for action, revision in [("downgrade", "0004_search_profiles"), ("upgrade", "head")]:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", action, revision],
            env=env,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, "Test-schema migration failed; credentials hidden"
    # Pooled prepared plans reference dropped/recreated relations; release those connections.
    await database.engine.dispose()
    async with database.sessions() as session:
        restored = await ListingService(session).page(user, 20, 0)
    assert restored == original
    async with database.sessions() as session:
        scan = await ListingCatalog(session).scan(user, [SOURCE])
    assert scan.scanned == 2 and len(scan.groups) == 2
