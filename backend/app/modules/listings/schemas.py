from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.urls import canonical_url, public_https_url

VisaStatus = Literal["CONFIRMED", "POSSIBLE", "RELOCATION", "NOT_SPECIFIED", "NONE"]


class ImportJob(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    original_url: str = Field(min_length=1, max_length=4096)
    application_url: str | None = Field(default=None, max_length=4096)
    source_job_id: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    domain: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    min_years: int | None = Field(default=None, ge=0, le=60)
    max_years: int | None = Field(default=None, ge=0, le=60)
    description: str | None = Field(default=None, max_length=50000)
    mandatory_skills: list[str] = Field(default_factory=list, max_length=100)
    optional_skills: list[str] = Field(default_factory=list, max_length=100)
    visa_status: VisaStatus = "NOT_SPECIFIED"
    visa_evidence: str | None = Field(default=None, max_length=2000)
    published_at: datetime | None = None

    @field_validator("original_url", "application_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        result = public_https_url(value)
        canonical_url(result)
        return result

    @field_validator(
        "title", "company", "description", "country", "city", "visa_evidence", mode="before"
    )
    @classmethod
    def strip_unknowns(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Publication date requires an explicit timezone")
        return value

    @field_validator("mandatory_skills", "optional_skills")
    @classmethod
    def validate_skills(cls, value: list[str]) -> list[str]:
        if any(not skill.strip() or len(skill) > 100 for skill in value):
            raise ValueError("Skills must be nonempty and at most 100 characters")
        return list(dict.fromkeys(skill.strip() for skill in value))

    @model_validator(mode="after")
    def validate_requirements(self) -> Self:
        if self.visa_status == "CONFIRMED" and not self.visa_evidence:
            raise ValueError("Confirmed sponsorship requires textual evidence")
        if (
            self.min_years is not None
            and self.max_years is not None
            and self.max_years < self.min_years
        ):
            raise ValueError("Maximum experience cannot be less than minimum experience")
        return self


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    jobs: list[ImportJob] = Field(min_length=1, max_length=200)
    confirm: Literal[True]


class CsvPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    csv_text: str = Field(min_length=1, max_length=524288)


class PreviewRow(BaseModel):
    row_number: int
    job: ImportJob | None
    errors: list[str]


class CsvPreview(BaseModel):
    rows: list[PreviewRow]
    valid_count: int
    invalid_count: int


class ListingView(BaseModel):
    id: UUID
    source_id: UUID
    source_name: str
    original_url: str
    canonical_url: str
    application_url: str
    title: str | None
    company: str | None
    country: str | None
    city: str | None
    description: str | None
    published_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    visa_status: str
    status: str
    missing_fields: list[str]


class ImportResult(BaseModel):
    batch_id: UUID
    created_count: int
    existing_count: int
    listings: list[ListingView]


class ListingsPage(BaseModel):
    items: list[ListingView]
    total: int
