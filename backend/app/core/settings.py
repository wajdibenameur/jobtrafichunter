import base64
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: SecretStr
    database_schema: str = Field(default="public", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    jwt_secret: SecretStr
    cv_encryption_key: SecretStr
    cv_storage_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "local-data" / "cvs"
    )
    cv_sandbox_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / ".cache" / "cv-sandbox"
    )
    allowed_origins: list[str] = Field(default_factory=lambda: ["https://localhost:8443"])
    environment: Literal["development", "production", "test"] = "development"
    access_minutes: int = Field(default=15, ge=1, le=15)
    refresh_days: int = Field(default=7, ge=1, le=30)
    login_max_failures: int = Field(default=5, ge=2, le=20)
    login_window_seconds: int = Field(default=900, ge=60)
    lockout_seconds: int = Field(default=900, ge=60)

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = (
                url.drivername == "postgresql+asyncpg"
                and bool(url.database)
                and bool(url.password)
                and "CHANGE_ME" not in value.get_secret_value()
            )
        except Exception:
            valid = False
        if not valid:
            raise ValueError("Set a PostgreSQL asyncpg URL with dedicated database credentials")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_signing_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) < 48 or len(set(raw)) < 12 or "CHANGE_ME" in raw:
            raise ValueError("Generate a random JWT_SECRET of at least 48 characters")
        return value

    @field_validator("cv_encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: SecretStr) -> SecretStr:
        try:
            key = base64.b64decode(value.get_secret_value(), validate=True)
        except Exception as exc:
            raise ValueError("CV_ENCRYPTION_KEY must be base64 encoded") from exc
        if len(key) != 32 or len(set(key)) < 12:
            raise ValueError("CV_ENCRYPTION_KEY must encode 32 random bytes")
        return value

    @model_validator(mode="after")
    def validate_origins(self) -> Self:
        if not self.allowed_origins or any(
            not self.valid_origin(origin) for origin in self.allowed_origins
        ):
            raise ValueError("ALLOWED_ORIGINS must contain explicit HTTPS origins")
        return self

    @staticmethod
    def valid_origin(origin: str) -> bool:
        try:
            url = urlsplit(origin)
            return (
                url.scheme == "https"
                and bool(url.hostname)
                and not url.path
                and not url.query
                and not url.fragment
                and not url.username
                and not url.password
                and "*" not in origin
                and url.port != 0
            )
        except ValueError:
            return False
