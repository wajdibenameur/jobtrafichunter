import asyncio

from sqlalchemy import Connection, text

from alembic import context
from app.core.db import Base, make_runtime
from app.core.settings import Settings
from app.modules.auth import AuthService  # public import registers the auth-owned tables

assert AuthService is not None
target_metadata = Base.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def migrate() -> None:
    runtime = make_runtime(Settings())
    try:
        async with runtime.engine.begin() as connection:
            # One transaction/connection for lock and migration: API/worker cannot race.
            await connection.execute(text("SELECT pg_advisory_xact_lock(746103002)"))
            await connection.run_sync(run_migrations)
    finally:
        await runtime.engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are disabled: use a dedicated PostgreSQL connection")
asyncio.run(migrate())
