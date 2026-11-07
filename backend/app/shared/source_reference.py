from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class SourceReference:
    id: UUID
    name: str
    manual_import_supported: bool


class SourceLookup(Protocol):
    async def __call__(self, user_id: UUID, source_id: UUID) -> SourceReference: ...
