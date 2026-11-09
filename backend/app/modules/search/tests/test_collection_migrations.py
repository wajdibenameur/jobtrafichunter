import asyncio
import os
import subprocess
import sys
from datetime import datetime

import httpx
import pytest
from sqlalchemy import select

from app.core.db import Runtime
from app.modules.listings import ListingService
from app.modules.search.queue import SearchQueue
from app.modules.search.schemas import ProfileInput, SearchCriteria
from app.modules.search.service import SearchService
from app.modules.search.tests.test_collection import job, page, request, setup, view
from app.modules.search.tests.test_queue import prepare
from app.modules.sources.models import CollectionConfig, CollectionReservation

pytestmark = pytest.mark.integration


async def test_collection_migrations_round_trip_and_no_schema_drift(database: Runtime) -> None:
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
    await database.engine.dispose()
    for args in [
        ("check",),
        ("downgrade", "0008_candidate_profiles"),
        ("upgrade", "head"),
        ("check",),
    ]:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", *args],
            env=env,
            capture_output=True,
            timeout=40,
        )
        assert result.returncode == 0, (
            "Disposable schema migration check failed; credentials hidden"
        )
    await database.engine.dispose()
    async with database.sessions() as session:
        assert await ListingService(session).page(user, 20, 0) == original


async def test_source_rate_reservation_shared_between_profiles(database: Runtime) -> None:
    from app.shared.clock import utcnow

    calls: list[datetime] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(utcnow())
        return page([job()])

    user, profile, source, service, adapters = await setup(database, handler)
    async with database.sessions() as session, session.begin():
        config = await session.get(CollectionConfig, source)
        assert config is not None
        config.limits = {"min_interval_seconds": 0.15}
    async with database.sessions() as session:
        second = await SearchService(session).create(
            user,
            ProfileInput(
                name="Parallel fixture",
                criteria=SearchCriteria(source_ids=[source], experience_levels=[]),
            ),
        )
    one = await request(database, user, profile, service)
    two = await request(database, user, second.id, service)
    assert all(
        await asyncio.gather(
            SearchQueue(database, adapters=adapters).run_once(),
            SearchQueue(database, adapters=adapters).run_once(),
        )
    )
    assert len(calls) == 2 and (calls[1] - calls[0]).total_seconds() >= 0.10
    assert (await view(database, user, one.id)).status == "SUCCEEDED"
    assert (await view(database, user, two.id)).status == "SUCCEEDED"
    async with database.sessions() as session:
        rows = list((await session.scalars(select(CollectionReservation))).all())
        assert len(rows) == 2 and all(r.settled for r in rows)
