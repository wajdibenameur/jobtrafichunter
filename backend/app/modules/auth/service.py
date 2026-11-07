from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import (
    access_token,
    decode_access,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.core.settings import Settings
from app.modules.auth.models import AuthSession
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import OwnerView
from app.shared.clock import utcnow


@dataclass(frozen=True)
class Tokens:
    access: str
    refresh: str
    owner: OwnerView


def unauthorized() -> AppError:
    return AppError("UNAUTHENTICATED", "Authentication required", 401)


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.repo = AuthRepository(session)
        self.settings = settings

    async def setup_owner(self, email: str, password: str) -> OwnerView:
        email = email.strip().casefold()
        if not 12 <= len(password) <= 128 or "@" not in email or len(email) > 254:
            raise AppError("INVALID_SETUP", "Use a valid email and a 12–128 character password")
        password_hash = await hash_password(password)
        async with self.session.begin():
            await self.repo.lock_setup()
            if await self.repo.owner() is not None:
                raise AppError("SETUP_LOCKED", "Owner already exists", 409)
            owner = await self.repo.add_owner(email, password_hash)
            return OwnerView(id=owner.id, email=owner.email)

    async def login(self, email: str, password: str, key: str) -> Tokens:
        now = utcnow()
        error: AppError | None = None
        tokens: Tokens | None = None
        async with self.session.begin():
            bucket = await self.repo.bucket(key)
            owner = await self.repo.owner(email, lock=True)
            locked = (bucket.locked_until is not None and bucket.locked_until > now) or (
                owner is not None and owner.locked_until is not None and owner.locked_until > now
            )
            if locked:
                error = AppError("LOGIN_LOCKED", "Try again later", 429)
            else:
                if (
                    now - bucket.window_start
                ).total_seconds() >= self.settings.login_window_seconds:
                    bucket.failures = 0
                    bucket.window_start = now
                    bucket.locked_until = None
                if owner is not None and owner.locked_until is not None:
                    owner.failures = 0
                    owner.locked_until = None
                # Unknown accounts still perform Argon2 work to limit enumeration timing.
                valid = await verify_password(owner.password_hash, password) if owner else False
                if owner is None:
                    await hash_password(password)
                if not valid or owner is None:
                    bucket.failures += 1
                    until = now + timedelta(seconds=self.settings.lockout_seconds)
                    if bucket.failures >= self.settings.login_max_failures:
                        bucket.locked_until = until
                    if owner is not None:
                        owner.failures += 1
                        if owner.failures >= self.settings.login_max_failures:
                            owner.locked_until = until
                    error = unauthorized()
                else:
                    owner.failures = 0
                    owner.locked_until = None
                    # Keep the IP failure budget even after a successful login.
                    refresh = new_refresh_token()
                    auth = AuthSession(
                        user_id=owner.id,
                        expires_at=now + timedelta(days=self.settings.refresh_days),
                    )
                    await self.repo.add_session(auth, hash_token(refresh))
                    tokens = Tokens(
                        access_token(owner.id, auth.id, self.settings),
                        refresh,
                        OwnerView(id=owner.id, email=owner.email),
                    )
        if error:
            raise error  # Failed-attempt counters have committed before this exception.
        assert tokens is not None
        return tokens

    async def rotate(self, raw_token: str) -> Tokens:
        now = utcnow()
        error: AppError | None = None
        tokens: Tokens | None = None
        async with self.session.begin():
            token = await self.repo.refresh(hash_token(raw_token))
            if token is None:
                error = unauthorized()
            else:
                auth = await self.repo.auth_session(token.session_id, lock=True)
                # Refresh again after locking the family to see a concurrent rotation.
                token = await self.repo.refresh(hash_token(raw_token))
                if auth is None or auth.revoked_at is not None or auth.expires_at <= now:
                    error = unauthorized()
                elif token is None or token.used_at is not None:
                    auth.revoked_at = now  # Reuse revokes the whole family, including access JWTs.
                    error = unauthorized()
                else:
                    owner = await self.repo.user(auth.user_id)
                    if owner is None:
                        error = unauthorized()
                    else:
                        token.used_at = now
                        refresh = new_refresh_token()
                        self.repo.add_refresh(auth.id, hash_token(refresh))
                        tokens = Tokens(
                            access_token(owner.id, auth.id, self.settings),
                            refresh,
                            OwnerView(id=owner.id, email=owner.email),
                        )
        if error:
            raise error
        assert tokens is not None
        return tokens

    async def current_owner(self, raw_access: str) -> OwnerView:
        claims = decode_access(raw_access, self.settings)
        auth = await self.repo.auth_session(claims.session_id)
        if (
            auth is None
            or auth.user_id != claims.user_id
            or auth.revoked_at is not None
            or auth.expires_at <= utcnow()
        ):
            raise unauthorized()
        owner = await self.repo.user(claims.user_id)
        if owner is None:
            raise unauthorized()
        return OwnerView(id=owner.id, email=owner.email)

    async def logout(self, raw_refresh: str) -> None:
        async with self.session.begin():
            token = await self.repo.refresh(hash_token(raw_refresh))
            if token is not None:
                auth = await self.repo.auth_session(token.session_id, lock=True)
                if auth is not None:
                    auth.revoked_at = utcnow()
