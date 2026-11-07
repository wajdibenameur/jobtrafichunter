from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SourcePreferenceChanged:
    user_id: UUID
    source_id: UUID
