from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.listings import ListingFact, ListingGroupView
from app.modules.matching import MatchingRunView
from app.modules.search.schemas import SearchCriteria


class ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    scope: Literal["IMPORTED_OFFERS", "COLLECTED_OFFERS", "MATCHING_ONLY"] = "IMPORTED_OFFERS"
    max_results: int | None = Field(default=None, ge=1, le=500)

    matching_preview: bool = False
    policy_id: UUID | None = None
    expected_candidate_id: UUID | None = None
    source_execution_id: UUID | None = None

    @model_validator(mode="after")
    def collection_options(self) -> "ExecutionInput":
        if self.scope != "COLLECTED_OFFERS" and self.max_results is not None:
            raise ValueError("Collection options require collection scope")
        if self.scope == "MATCHING_ONLY":
            if not self.matching_preview or self.source_execution_id is None:
                raise ValueError("Re-scoring requires an explicit preview and a source execution")
        elif self.source_execution_id is not None:
            raise ValueError("Source execution requires matching-only scope")
        if not self.matching_preview and (self.policy_id or self.expected_candidate_id):
            raise ValueError("Matching options require explicit preview")
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
    scope: Literal["IMPORTED_OFFERS", "COLLECTED_OFFERS", "MATCHING_ONLY"] = "IMPORTED_OFFERS"
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
    matching: MatchingRunView | None = None


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
