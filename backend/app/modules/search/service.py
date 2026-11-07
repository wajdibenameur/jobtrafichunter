from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.search.models import SearchConfiguration, SearchProfile
from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import ProfileInput, ProfileView, SearchCriteria
from app.shared.clock import utcnow


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SearchRepository(session)

    async def _get(self, user_id: UUID, profile_id: UUID, *, lock: bool = False) -> SearchProfile:
        row = await self.repo.profile(user_id, profile_id, lock=lock)
        if row is None:
            raise AppError("PROFILE_NOT_FOUND", "Search profile not found", 404)
        return row

    async def _view(self, row: SearchProfile) -> ProfileView:
        config = await self.session.get(SearchConfiguration, row.id)
        assert config is not None
        return ProfileView(
            id=row.id,
            name=row.name,
            description=row.description,
            criteria=SearchCriteria.model_validate(config.criteria),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def profiles(self, user_id: UUID) -> list[ProfileView]:
        return [await self._view(row) for row in await self.repo.profiles(user_id)]

    async def get(self, user_id: UUID, profile_id: UUID) -> ProfileView:
        return await self._view(await self._get(user_id, profile_id))

    async def _add(self, user_id: UUID, body: ProfileInput, seed: str | None = None) -> ProfileView:
        if len(await self.repo.profiles(user_id)) >= 100:
            raise AppError("PROFILE_LIMIT", "At most 100 active profiles are supported", 409)
        row = SearchProfile(
            user_id=user_id, name=body.name, description=body.description, seed_key=seed
        )
        self.session.add(row)
        await self.session.flush()
        self.session.add(
            SearchConfiguration(profile_id=row.id, criteria=body.criteria.model_dump(mode="json"))
        )
        await self.session.flush()
        return await self._view(row)

    async def create(self, user_id: UUID, body: ProfileInput) -> ProfileView:
        async with self.session.begin():
            return await self._add(user_id, body)

    async def update(self, user_id: UUID, profile_id: UUID, body: ProfileInput) -> ProfileView:
        async with self.session.begin():
            row = await self._get(user_id, profile_id, lock=True)
            config = await self.session.get(SearchConfiguration, profile_id)
            assert config is not None
            row.name, row.description, row.updated_at = body.name, body.description, utcnow()
            config.criteria = body.criteria.model_dump(mode="json")
            await self.session.flush()
            return await self._view(row)

    async def delete(self, user_id: UUID, profile_id: UUID) -> None:
        async with self.session.begin():
            row = await self._get(user_id, profile_id, lock=True)
            row.archived = True
            row.updated_at = utcnow()

    async def duplicate(self, user_id: UUID, profile_id: UUID, name: str) -> ProfileView:
        async with self.session.begin():
            original = await self._view(await self._get(user_id, profile_id))
            return await self._add(
                user_id,
                ProfileInput(
                    name=name, description=original.description, criteria=original.criteria
                ),
            )

    async def examples(self, user_id: UUID) -> list[ProfileView]:
        async with self.session.begin():
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": user_id.int & ((1 << 63) - 1)}
            )
            existing = set(
                (
                    await self.session.scalars(
                        select(SearchProfile.seed_key).where(SearchProfile.user_id == user_id)
                    )
                ).all()
            )
            templates = [
                (
                    "tunisia",
                    "Tunisia Junior Developer",
                    SearchCriteria(
                        countries=["Tunisia"], include_keywords=["Developer", "Développeur"]
                    ),
                ),
                (
                    "europe",
                    "Europe Visa Sponsorship",
                    SearchCriteria(
                        countries=["France", "Germany", "Portugal"],
                        visa_statuses=["CONFIRMED", "RELOCATION"],
                    ),
                ),
                ("remote", "Remote International", SearchCriteria(work_modes=["remote"])),
            ]
            for key, name, criteria in templates:
                if key not in existing:
                    await self._add(user_id, ProfileInput(name=name, criteria=criteria), key)
            return await self.profiles(user_id)
