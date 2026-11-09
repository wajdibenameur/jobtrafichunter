from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ShortText = Annotated[str, Field(min_length=1, max_length=1000)]


class CandidateFields(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    professional_title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=3000)
    education: list[ShortText] = Field(default_factory=list, max_length=30)
    experiences: list[ShortText] = Field(default_factory=list, max_length=30)
    languages: list[ShortText] = Field(default_factory=list, max_length=30)
    certifications: list[ShortText] = Field(default_factory=list, max_length=30)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    years_experience: float | None = Field(default=None, ge=0, le=60)

    @field_validator("professional_title", "summary")
    @classmethod
    def nullable_text(cls, value: str | None) -> str | None:
        if value is not None and "\x00" in value:
            raise ValueError("Invalid text")
        return value.strip() or None if value else None

    @field_validator("education", "experiences", "languages", "certifications")
    @classmethod
    def nonempty_records(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or "\x00" in item for item in value):
            raise ValueError("Invalid record")
        return [item.strip() for item in value]

    @field_validator("skills")
    @classmethod
    def bounded_skills(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        if len(value) > 12 or any(
            not key.strip()
            or len(key) > 50
            or len(items) > 100
            or any(not item.strip() or len(item) > 100 for item in items)
            for key, items in value.items()
        ):
            raise ValueError("Invalid skill categories")
        return {
            key: list(dict.fromkeys(item.strip() for item in items)) for key, items in value.items()
        }


class CandidatePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locations: list[ShortText] = Field(default_factory=list, max_length=30)
    domains: list[ShortText] = Field(default_factory=list, max_length=30)
    target_levels: list[ShortText] = Field(default_factory=list, max_length=10)
    visa_needed: bool | None = None


class CandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    fields: CandidateFields
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)


class Evidence(BaseModel):
    page: int = Field(ge=1, le=50)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = Field(max_length=3000, repr=False)


class ProfilePayload(CandidateInput):
    evidence: dict[str, list[Evidence]] = Field(default_factory=dict, repr=False)
    origins: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    parser_version: str = "local-rules-v1"
    document_parser_version: str = "unknown"
    taxonomy: dict[str, int] = Field(default_factory=dict)


class CandidateView(BaseModel):
    id: UUID
    cv_version_id: UUID
    parent_id: UUID | None
    revision: int
    status: str
    active: bool
    created_at: datetime
    validated_at: datetime | None
    data: ProfilePayload = Field(repr=False)
    changed_fields: list[str]
    unknown_fields: list[str]


class GenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    regenerate: bool = False


class ValidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewed: Literal[True]
