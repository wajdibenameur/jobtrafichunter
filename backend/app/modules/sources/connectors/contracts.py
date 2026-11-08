from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class NormalizedListing(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    original_url: str = Field(max_length=4096)
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    _url = field_validator("original_url")(public_https_url)


class ConnectorPage(BaseModel):
    """One bounded page; a missing checkpoint must not conceal truncation."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    items: list[NormalizedListing] = Field(default_factory=list, max_length=500)
    next_cursor: str | None = Field(default=None, max_length=2048)
    truncated: bool = False


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
