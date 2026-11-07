from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SearchRequested:
    execution_id: UUID
    user_id: UUID
