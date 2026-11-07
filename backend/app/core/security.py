import asyncio
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.errors import AppError
from app.core.settings import Settings
from app.shared.clock import utcnow

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
ISSUER = "jobhunter"
AUDIENCE = "jobhunter-owner"


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(PASSWORD_HASHER.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    try:
        return await asyncio.to_thread(PASSWORD_HASHER.verify, password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_key(address: str, secret: str) -> str:
    return hmac.new(secret.encode(), address.encode(), hashlib.sha256).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def access_token(user_id: UUID, session_id: UUID, settings: Settings) -> str:
    now = utcnow()
    return jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_minutes),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "type": "access",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


@dataclass(frozen=True)
class AccessClaims:
    user_id: UUID
    session_id: UUID


def decode_access(token: str, settings: Settings) -> AccessClaims:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "sid", "jti", "type"]},
        )
        if claims["type"] != "access":
            raise ValueError("Wrong token type")
        return AccessClaims(UUID(claims["sub"]), UUID(claims["sid"]))
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise AppError("UNAUTHENTICATED", "Authentication required", 401) from exc
