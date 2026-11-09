from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.listings import ListingFact, ListingGroupView
from app.modules.search.schemas import SearchCriteria


class ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    scope: Literal["IMPORTED_OFFERS", "COLLECTED_OFFERS"] = "IMPORTED_OFFERS"
    max_results: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def collection_options(self) -> "ExecutionInput":
        if self.scope == "IMPORTED_OFFERS" and self.max_results is not None:
            raise ValueError("Collection options require collection scope")
        return self


class SourceLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: UUID
    source_name: str
    status: str
    reason: str
    counts: dict[str, int] | None = None


class ExecutionView(BaseModel):
    id: UUID
    profile_id: UUID
    profile_name: str
    scope: Literal["IMPORTED_OFFERS", "COLLECTED_OFFERS"] = "IMPORTED_OFFERS"
    status: str
    criteria: SearchCriteria
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    counts: dict[str, int]
    reason: str | None
    stage: str
    cursor: int
    attempt: int
    heartbeat_at: datetime | None
    sources: list[SourceLogView]


class ResultView(BaseModel):
    group: ListingGroupView
    listing: ListingFact
    unknown_fields: list[str]


class ResultsPage(BaseModel):
    items: list[ResultView]
    total: int


class DashboardView(BaseModel):
    imported_count: int
    last_execution: ExecutionView | None
