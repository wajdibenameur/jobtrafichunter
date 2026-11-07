from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.urls import public_https_url


class ConnectorFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ConnectorQuery(BaseModel):
    keywords: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    cursor: str | None = Field(default=None, max_length=2048)


@dataclass(frozen=True)
class Capabilities:
    automated: bool = False
    manual_import: bool = True
    search_link: bool = True


class NormalizedListing(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    original_url: str = Field(max_length=4096)
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    _url = field_validator("original_url")(public_https_url)


class JobSourceConnector(Protocol):
    def capabilities(self) -> Capabilities: ...
    async def health_check(self) -> Literal["MANUAL_ONLY"]: ...
    async def fetch(self, query: ConnectorQuery) -> list[NormalizedListing]: ...
    def normalize(self, raw: dict[str, object]) -> NormalizedListing: ...
