from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.shared.clock import utcnow


class JobListing(Base):
    __tablename__ = "job_listings"
    __table_args__ = (
        UniqueConstraint("user_id", "canonical_url", name="uq_listing_owner_url"),
        UniqueConstraint(
            "user_id", "source_id", "source_job_id", name="uq_listing_owner_source_job"
        ),
        CheckConstraint(
            "status IN ('ACTIVE','EXPIRED','REPOSTED','CLOSED')", name="ck_listing_status"
        ),
        CheckConstraint(
            "visa_status IN ('CONFIRMED','POSSIBLE','RELOCATION','NOT_SPECIFIED','NONE')",
            name="ck_listing_visa",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(100))
    source_job_id: Mapped[str | None] = mapped_column(String(200))
    original_url: Mapped[str] = mapped_column(String(4096))
    canonical_url: Mapped[str] = mapped_column(String(4096))
    application_url: Mapped[str] = mapped_column(String(4096))
    title: Mapped[str | None] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    work_mode: Mapped[str | None] = mapped_column(String(20))
    domain: Mapped[str | None] = mapped_column(String(100))
    experience_level: Mapped[str | None] = mapped_column(String(50))
    min_years: Mapped[int | None]
    max_years: Mapped[int | None]
    description: Mapped[str | None] = mapped_column(Text)
    mandatory_skills: Mapped[list[str]] = mapped_column(JSONB, default=list)
    optional_skills: Mapped[list[str]] = mapped_column(JSONB, default=list)
    visa_status: Mapped[str] = mapped_column(String(20), default="NOT_SPECIFIED")
    visa_evidence: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    repost_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("job_listings.id"))


class ImportBatch(Base):
    __tablename__ = "listing_import_batches"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    row_count: Mapped[int]
    created_count: Mapped[int]
    existing_count: Mapped[int]


class ImportRecord(Base):
    __tablename__ = "listing_import_records"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("listing_import_batches.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"))
    row_number: Mapped[int]
    disposition: Mapped[str] = mapped_column(String(20))
