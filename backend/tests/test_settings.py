import pytest
from pydantic import ValidationError

from app.core.settings import Settings


@pytest.mark.parametrize(
    "field,value",
    [
        ("jwt_secret", "CHANGE_ME"),
        ("jwt_secret", "x" * 64),
        ("cv_encryption_key", "not-base64"),
        ("cv_encryption_key", "eA=="),
        ("database_url", "sqlite:///database.db"),
        ("database_url", "postgresql+asyncpg://user:CHANGE_ME@localhost/db"),
        ("allowed_origins", ["*"]),
        ("allowed_origins", ["http://localhost:4200"]),
        ("allowed_origins", []),
        ("allowed_origins", ["https://localhost/path"]),
        ("allowed_origins", ["https://user@localhost"]),
    ],
)
def test_insecure_settings_rejected(settings: Settings, field: str, value: object) -> None:
    data = settings.model_dump()
    data[field] = value
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **data)
    assert str(value) not in str(error.value)


def test_secret_repr_is_redacted(settings: Settings) -> None:
    assert settings.jwt_secret.get_secret_value() not in repr(settings)
    assert settings.database_url.get_secret_value() not in repr(settings)
