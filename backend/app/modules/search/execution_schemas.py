from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.listings import ListingFact, ListingGroupView
from app.modules.search.schemas import SearchCriteria


class ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID


class SourceLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: UUID
    source_name: str
    status: str
    reason: str


class ExecutionView(BaseModel):
    id: UUID
    profile_id: UUID
    profile_name: str
    scope: Literal["IMPORTED_OFFERS"] = "IMPORTED_OFFERS"
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
