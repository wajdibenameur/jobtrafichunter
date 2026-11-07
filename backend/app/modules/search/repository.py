from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.models import SearchProfile


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def profiles(self, user_id: UUID) -> list[SearchProfile]:
        return list(
            (
                await self.session.scalars(
                    select(SearchProfile)
                    .where(SearchProfile.user_id == user_id, SearchProfile.archived.is_(False))
                    .order_by(SearchProfile.created_at, SearchProfile.id)
                )
            ).all()
        )

    async def profile(
        self, user_id: UUID, profile_id: UUID, *, lock: bool = False
    ) -> SearchProfile | None:
        query = select(SearchProfile).where(
            SearchProfile.user_id == user_id,
            SearchProfile.id == profile_id,
            SearchProfile.archived.is_(False),
        )
        if lock:
            query = query.with_for_update()
        return (await self.session.scalars(query)).one_or_none()
