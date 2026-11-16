from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.ai import JobAnalysis, JobInput, SkillDefinition
from app.modules.profile import MatchingCandidate

WEIGHTS = {
    "mandatory": 35,
    "optional": 10,
    "experience": 20,
    "title": 10,
    "languages": 10,
    "location": 5,
    "education": 5,
    "visa": 5,
}
Weight = Annotated[int, Field(strict=True, ge=0, le=100)]


class ScoringPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    weights: dict[str, Weight] = Field(default_factory=lambda: dict(WEIGHTS))
    mandatory_cap: int = Field(default=60, ge=0, le=60)

    @model_validator(mode="after")
    def valid_weights(self) -> Self:
        if set(self.weights) != set(WEIGHTS) or sum(self.weights.values()) != 100:
            raise ValueError("All eight weights must sum to 100")
        return self


class MatchJobInput(JobInput):
    group_id: UUID


class ScorePart(BaseModel):
    name: str
    weight: int
    points: float
    state: Literal["KNOWN", "UNKNOWN", "CONFLICT"]
    matched: list[str] = Field(default_factory=list)
    unattested: list[str] = Field(default_factory=list)


class MatchPreview(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    score: int = Field(ge=0, le=100)
    uncapped_score: int = Field(ge=0, le=100)
    coverage: int = Field(ge=0, le=100)
    provisional: Literal[True] = True
    confidence: Literal["LOW"] = "LOW"
    calibration_status: Literal["UNVALIDATED"] = "UNVALIDATED"
    scoring_version: str = "preview-rules-v1"
    provider: Literal["none"] = "none"
    components: list[ScorePart]
    cap_reasons: list[str]
    warnings: list[str]
    analysis: JobAnalysis = Field(repr=False)


class MatchingSnapshot(BaseModel):
    candidate: MatchingCandidate = Field(repr=False)
    taxonomy: list[SkillDefinition] = Field(repr=False, max_length=1200)
    policy: ScoringPolicy


class MatchingRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    execution_id: UUID
    candidate_id: UUID
    cv_version_id: UUID
    candidate_revision: int
    policy_version: int
    policy_id: UUID
    status: str
    cursor: int
    total: int
    cache_hits: int
    provisional: Literal[True] = True


class PolicyView(BaseModel):
    id: UUID
    version: int
    policy: ScoringPolicy


class MatchItem(BaseModel):
    group_id: UUID
    listing_id: UUID
    preview: MatchPreview = Field(repr=False)


class MatchingPage(BaseModel):
    run: MatchingRunView
    items: list[MatchItem]
