from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Label = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00]+$"),
]
Terms = Annotated[list[Label], Field(max_length=100)]


class SearchCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ids: list[UUID] = Field(default_factory=list, max_length=100)
    domains: Terms = Field(default_factory=list)
    titles: Terms = Field(default_factory=list)
    include_keywords: Terms = Field(default_factory=list)
    exclude_keywords: Terms = Field(default_factory=list)
    countries: Terms = Field(default_factory=list)
    cities: Terms = Field(default_factory=list)
    work_modes: list[Literal["remote", "hybrid", "onsite"]] = Field(
        default_factory=list, max_length=3
    )
    experience_levels: Terms = Field(default_factory=lambda: ["Graduate", "Entry Level", "Junior"])
    max_years: int = Field(default=3, ge=0, le=60)
    visa_statuses: list[Literal["CONFIRMED", "POSSIBLE", "RELOCATION", "NOT_SPECIFIED", "NONE"]] = (
        Field(default_factory=list, max_length=5)
    )
    publication_days: Literal[0, 1, 3, 7, 30] = 0
    publication_minutes: Literal[120, 360, 1440] | None = None
    novelty: Literal["all", "today", "24h", "3d", "7d", "30d"] = "all"
    unknown_policy: Literal["include", "exclude"] = "include"
    mode: Literal["MANUAL", "CV", "HYBRID"] = "MANUAL"
    linked_cv_id: UUID | None = None
    min_score: int = Field(default=0, ge=0, le=100)
    notifications_enabled: bool = False

    @model_validator(mode="after")
    def one_publication_window(self) -> Self:
        if self.publication_minutes is not None and self.publication_days:
            raise ValueError("Choose one publication window")
        return self

    @field_validator(
        "source_ids",
        "domains",
        "titles",
        "include_keywords",
        "exclude_keywords",
        "countries",
        "cities",
        "work_modes",
        "experience_levels",
        "visa_statuses",
    )
    @classmethod
    def unique_items(cls, values: list[object]) -> list[object]:
        return list(dict.fromkeys(values))


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Label
    description: str = Field(default="", max_length=500, pattern=r"^[^\x00]*$")
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)


class ProfileView(ProfileInput):
    id: UUID
    created_at: datetime
    updated_at: datetime


class DuplicateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Label
