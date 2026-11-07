from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sources.models import JobSource, SourcePreference


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: UUID) -> list[JobSource]:
        query = (
            select(JobSource)
            .where(
                JobSource.archived.is_(False),
                or_(JobSource.user_id.is_(None), JobSource.user_id == user_id),
            )
            .order_by(JobSource.created_at, JobSource.name)
        )
        return list((await self.session.scalars(query)).all())

    async def get(self, user_id: UUID, source_id: UUID) -> JobSource | None:
        query = select(JobSource).where(
            JobSource.id == source_id,
            JobSource.archived.is_(False),
            or_(JobSource.user_id.is_(None), JobSource.user_id == user_id),
        )
        return (await self.session.scalars(query)).one_or_none()

    async def preference(self, user_id: UUID, source_id: UUID) -> SourcePreference | None:
        return (
            await self.session.scalars(
                select(SourcePreference).where(
                    SourcePreference.user_id == user_id,
                    SourcePreference.source_id == source_id,
                )
            )
        ).one_or_none()

    async def save_preference(
        self, user_id: UUID, source_id: UUID, values: dict[str, object]
    ) -> None:
        statement = insert(SourcePreference).values(user_id=user_id, source_id=source_id, **values)
        await self.session.execute(
            statement.on_conflict_do_update(
                constraint="uq_source_preference_owner",
                set_=values,
            )
        )

    async def add(self, row: JobSource) -> None:
        self.session.add(row)
        await self.session.flush()
