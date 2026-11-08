from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.urls import public_https_url


class ConnectorFailure(Exception):
    def __init__(self, code: str, message: str, *, retry_after: float | None = None) -> None:
        self.code = code
        self.retry_after = retry_after
        super().__init__(message)


class ConnectorQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    keywords: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    cursor: str | None = Field(default=None, max_length=2048)
    limit: int = Field(default=10, ge=1, le=500)
    publication_minutes: int | None = Field(default=None, ge=1, le=43200)


@dataclass(frozen=True)
class Capabilities:
    automated: bool = False
    manual_import: bool = True
    search_link: bool = True
    pagination: bool = False
    publication_filter: bool = False


class NormalizedLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    label: str | None = Field(default=None, max_length=200)


class NormalizedListing(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    original_url: str = Field(max_length=4096)
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    source_job_id: str | None = Field(default=None, max_length=200)
    application_url: str | None = Field(default=None, max_length=4096)
    locations: list[NormalizedLocation] = Field(default_factory=list, max_length=30)
    applicant_locations: list[str] = Field(default_factory=list, max_length=30)
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    employment_types: list[str] = Field(default_factory=list, max_length=30)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_requirements: str | None = Field(default=None, max_length=4000)
    published_at: datetime | None = None
    published_date: date | None = None
    publication_raw: str | None = Field(default=None, max_length=128)
    publication_precision: Literal["UNKNOWN", "DATE", "LOCAL_DATETIME", "INSTANT"] = "UNKNOWN"
    source_document_url: str | None = Field(default=None, max_length=4096, repr=False)
    source_payload_hash: str | None = Field(default=None, max_length=64)
    extractor_version: str | None = Field(default=None, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("original_url", "application_url", "source_document_url")
    @classmethod
    def url(cls, value: str | None) -> str | None:
        return public_https_url(value) if value is not None else None

    @field_validator("published_at")
    @classmethod
    def aware_publication(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Publication instant requires an explicit timezone")
        return value

    @model_validator(mode="after")
    def consistent_publication(self) -> Self:
        if self.publication_precision == "INSTANT":
            valid = self.published_at is not None and self.published_date is None
        elif self.publication_precision in {"DATE", "LOCAL_DATETIME"}:
            valid = self.published_at is None and self.published_date is not None
        else:
            valid = self.published_at is None and self.published_date is None
        if not valid:
            raise ValueError("Publication precision must agree with its known value")
        return self


class ConnectorPage(BaseModel):
    """One bounded page; a missing checkpoint must not conceal truncation."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    items: list[NormalizedListing] = Field(default_factory=list, max_length=500)
    next_cursor: str | None = Field(default=None, max_length=2048)
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list, max_length=100)
    partial: bool = False
    matched_count: int | None = Field(default=None, ge=0)
    invalid_count: int = Field(default=0, ge=0)


class CollectionLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_requests: int = Field(default=20, ge=1, le=100)
    max_pages: int = Field(default=10, ge=1, le=50)
    max_results: int = Field(default=10, ge=1, le=500)
    max_redirects: int = Field(default=3, ge=0, le=5)
    max_attempts: int = Field(default=3, ge=1, le=3)
    max_wire_bytes: int = Field(default=2_097_152, ge=1, le=5_242_880)
    max_body_bytes: int = Field(default=2_097_152, ge=1, le=5_242_880)
    max_total_bytes: int = Field(default=10_485_760, ge=1, le=52_428_800)
    timeout_seconds: float = Field(default=15, gt=0, le=30, allow_inf_nan=False)
    duration_seconds: float = Field(default=180, gt=0, le=180, allow_inf_nan=False)
    min_interval_seconds: float = Field(default=60, ge=0.01, le=86400, allow_inf_nan=False)


@dataclass(frozen=True)
class CollectedResponse:
    url: str = field(repr=False)
    content_type: str
    body: bytes = field(repr=False)
    observed_at: datetime


class JobSourceConnector(Protocol):
    def capabilities(self) -> Capabilities: ...
    async def health_check(self) -> Literal["MANUAL_ONLY", "READY", "UNAVAILABLE"]: ...
    async def fetch(self, query: ConnectorQuery) -> list[NormalizedListing]: ...
    async def fetch_page(self, query: ConnectorQuery) -> ConnectorPage: ...
    def normalize(self, raw: dict[str, object]) -> NormalizedListing: ...
