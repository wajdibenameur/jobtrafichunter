from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.shared.clock import utcnow


class CandidateProfileVersion(Base):
    __tablename__ = "candidate_profile_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cv_version_id", "user_id"],
            ["cv_versions.id", "cv_versions.user_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("cv_version_id", "revision", name="uq_candidate_revision"),
        UniqueConstraint("id", "user_id", name="uq_candidate_owner"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(index=True)
    cv_version_id: Mapped[UUID] = mapped_column(index=True)
    # Parent may belong to the previous original version; retain the diff while
    # both documents live. No link to any other owner's data is created by service.
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("candidate_profile_versions.id", ondelete="SET NULL")
    )
    revision: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    private_payload: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActiveCandidateProfile(Base):
    __tablename__ = "active_candidate_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "user_id"],
            ["candidate_profile_versions.id", "candidate_profile_versions.user_id"],
            ondelete="CASCADE",
        ),
    )
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(unique=True)
