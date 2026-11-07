from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import Settings


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def make_runtime(settings: Settings) -> Runtime:
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        echo=False,
        hide_parameters=True,
        connect_args={"timeout": 5, "server_settings": {"search_path": settings.database_schema}},
    )
    return Runtime(settings, engine, async_sessionmaker(engine, expire_on_commit=False))


def get_runtime(request: Request) -> Runtime:
    return cast(Runtime, request.app.state.runtime)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with get_runtime(request).sessions() as session:
        yield session


async def get_business_session(request: Request) -> AsyncIterator[AsyncSession]:
    # Distinct dependency: auth's read transaction must not own business transactions.
    async with get_runtime(request).sessions() as session:
        yield session
