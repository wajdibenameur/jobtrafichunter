"""Plain document inspection contract shared without module dependencies."""

from collections.abc import Awaitable
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class DocumentPage(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    number: int = Field(ge=1, le=50)
    text: str = Field(max_length=50000, repr=False)


class DocumentInspection(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    status: Literal["TEXT", "NEEDS_OCR"]
    kind: Literal["PDF", "DOCX"]
    parser_version: str = Field(default="unknown", max_length=60)
    pages: list[DocumentPage] = Field(min_length=1, max_length=50, repr=False)


class DocumentInspector(Protocol):
    def __call__(
        self, content: bytes, filename: str, content_type: str
    ) -> Awaitable[DocumentInspection]: ...
