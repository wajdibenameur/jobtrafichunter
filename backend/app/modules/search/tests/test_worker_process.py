import asyncio
import os
import subprocess
import sys

import pytest

from app.core.db import Runtime
from app.modules.search.executions import ExecutionService
from app.modules.search.tests.test_queue import prepare, request


@pytest.mark.integration
async def test_worker_claims_pending_task_in_a_clean_process(database: Runtime) -> None:
    user, profile = await prepare(database)
    identifier = await request(database, user, profile)
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
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "app.worker", "--once"],
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, "Isolated worker failed; credentials hidden"
    async with database.sessions() as session:
        execution = await ExecutionService(session).get(user, identifier)
    assert execution.status == "SUCCEEDED" and execution.counts["results"] == 2
