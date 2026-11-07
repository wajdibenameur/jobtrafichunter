from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.urls import public_https_url


class SourceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keywords: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)


class SourcePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    settings: SourceSettings | None = None

    @field_validator("display_name")
    @classmethod
    def validate_label(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A display name cannot be blank")
        return value.strip() if value else value


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    homepage: str = Field(max_length=4096)
    region: Literal["TN", "GLOBAL"] = "GLOBAL"
    _url = field_validator("homepage")(public_https_url)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A source name cannot be blank")
        return value.strip()


class SourceView(BaseModel):
    id: UUID
    slug: str
    name: str
    homepage: str
    region: str
    integration_type: str
    legal_status: str
    enabled: bool
    automation_eligible: bool
    manual_import_supported: bool
    custom: bool
    settings: SourceSettings
    health_status: Literal["MANUAL_ONLY", "UNVERIFIED", "DISABLED"]
    last_successful_sync: datetime | None = None
    jobs_collected: int | None = None
    reason: str


class SearchLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keywords: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)


class SearchLinkView(BaseModel):
    url: str
    criteria_applied: bool
