from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PolicyRow(Base):
    __tablename__ = "scoring_policies"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_scoring_policy_version"),
        UniqueConstraint("user_id", "config_hash", name="uq_scoring_policy_hash"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int]
    config_hash: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict[str, object]] = mapped_column(JSONB)


class MatchingRun(Base):
    __tablename__ = "matching_runs"
    __table_args__ = (
        CheckConstraint(
            "cursor >= 0 AND total >= 0 AND cache_hits >= 0", name="ck_matching_counts"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), unique=True
    )
    source_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("search_executions.id", ondelete="SET NULL")
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profile_versions.id", ondelete="CASCADE"), index=True
    )
    cv_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="CASCADE"), index=True
    )
    candidate_revision: Mapped[int]
    policy_version: Mapped[int]
    policy_id: Mapped[UUID] = mapped_column(ForeignKey("scoring_policies.id"))
    private_snapshot: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    cursor: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    cache_hits: Mapped[int] = mapped_column(default=0)


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("run_id", "group_id", name="uq_match_run_group"),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_match_score"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("matching_runs.id", ondelete="CASCADE"), index=True
    )
    group_id: Mapped[UUID]
    listing_id: Mapped[UUID]
    analysis_id: Mapped[UUID] = mapped_column(ForeignKey("job_analyses.id"))
    cache_key: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[int]
    private_payload: Mapped[bytes] = mapped_column(LargeBinary)
