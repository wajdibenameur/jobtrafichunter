from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field


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
    original_url: str
    title: str | None = None
    company: str | None = None
    description: str | None = None


class JobSourceConnector(Protocol):
    def capabilities(self) -> Capabilities: ...
    async def health_check(self) -> Literal["MANUAL_ONLY"]: ...
    async def fetch(self, query: ConnectorQuery) -> list[NormalizedListing]: ...
    def normalize(self, raw: dict[str, object]) -> NormalizedListing: ...
