from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListingImported:
    user_id: UUID
    listing_id: UUID
