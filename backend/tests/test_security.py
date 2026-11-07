from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.errors import AppError
from app.core.security import (
    AUDIENCE,
    ISSUER,
    access_token,
    client_key,
    decode_access,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.core.settings import Settings
from app.shared.clock import utcnow


async def test_argon2id_and_wrong_password() -> None:
    encoded = await hash_password("fixture-password-long")
    assert encoded.startswith("$argon2id$")
    assert await verify_password(encoded, "fixture-password-long")
    assert not await verify_password(encoded, "wrong")
    assert not await verify_password("invalid-hash", "wrong")


def test_access_roundtrip_and_tampering(settings: Settings) -> None:
    user_id, session_id = uuid4(), uuid4()
    token = access_token(user_id, session_id, settings)
    assert decode_access(token, settings).user_id == user_id
    assert decode_access(token, settings).session_id == session_id
    with pytest.raises(AppError):
        decode_access(token + "tampered", settings)


@pytest.mark.parametrize("kind", ["expired", "wrong_audience", "wrong_type", "missing_claim"])
def test_invalid_claims_rejected(settings: Settings, kind: str) -> None:
    now = utcnow()
    claims = {
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "type": "access",
    }
    if kind == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    elif kind == "wrong_audience":
        claims["aud"] = "other-service"
    elif kind == "wrong_type":
        claims["type"] = "refresh"
    else:
        del claims["sid"]
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(AppError):
        decode_access(token, settings)


def test_refresh_random_and_hash_only() -> None:
    first, second = new_refresh_token(), new_refresh_token()
    assert len(first) >= 64 and first != second
    assert hash_token(first) != first
    assert len(hash_token(first)) == 64
    assert hash_token(first) == hash_token(first)


def test_client_keys_do_not_expose_ip() -> None:
    assert "127.0.0.1" not in client_key("127.0.0.1", "secret-a")
    assert client_key("127.0.0.1", "secret-a") != client_key("127.0.0.1", "secret-b")
