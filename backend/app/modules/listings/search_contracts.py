from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListingFact(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    source_name: str
    source_job_id: str | None
    original_url: str
    canonical_url: str
    application_url: str
    title: str | None
    company: str | None
    country: str | None
    city: str | None
    work_mode: str | None
    domain: str | None
    experience_level: str | None
    min_years: int | None
    max_years: int | None
    description: str | None
    mandatory_skills: list[str]
    optional_skills: list[str]
    visa_status: str
    visa_evidence: str | None
    published_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    status: str


class ListingGroupView(BaseModel):
    id: UUID
    first_seen_at: datetime
    members: list[ListingFact]
    candidate_ids: list[UUID]
    repost_of_id: UUID | None
    policy_version: str
    provenance: list[ListingLink]
    novelty_verified: bool = True


class ListingLink(BaseModel):
    listing_id: UUID
    source_id: UUID
    source_name: str
    original_url: str
    application_url: str


class ListingScan(BaseModel):
    groups: list[ListingGroupView]
    scanned: int
    duplicates: int
    truncated: bool
