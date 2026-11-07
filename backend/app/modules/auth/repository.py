from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AppUser, AuthSession, LoginBucket, RefreshToken


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_setup(self) -> None:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(746103001)"))

    async def owner(self, email: str | None = None, *, lock: bool = False) -> AppUser | None:
        query = select(AppUser)
        if email is not None:
            query = query.where(AppUser.email == email)
        if lock:
            query = query.with_for_update()
        return (await self.session.scalars(query)).one_or_none()

    async def bucket(self, key: str) -> LoginBucket:
        await self.session.execute(insert(LoginBucket).values(key=key).on_conflict_do_nothing())
        row = await self.session.scalar(
            select(LoginBucket).where(LoginBucket.key == key).with_for_update(),
        )
        assert row is not None
        return row

    async def auth_session(self, session_id: UUID, *, lock: bool = False) -> AuthSession | None:
        query = select(AuthSession).where(AuthSession.id == session_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self.session.scalars(query)).one_or_none()

    async def refresh(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.scalars(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .execution_options(populate_existing=True),
        )
        return result.one_or_none()

    async def user(self, user_id: UUID) -> AppUser | None:
        return await self.session.get(AppUser, user_id)

    async def add_owner(self, email: str, password_hash: str) -> AppUser:
        row = AppUser(email=email, password_hash=password_hash)
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_session(self, row: AuthSession, token_hash: str) -> None:
        self.session.add(row)
        await self.session.flush()
        self.add_refresh(row.id, token_hash)

    def add_refresh(self, session_id: UUID, token_hash: str) -> None:
        self.session.add(RefreshToken(session_id=session_id, token_hash=token_hash))
