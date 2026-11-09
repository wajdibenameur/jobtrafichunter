from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.shared.clock import utcnow


class SearchProfile(Base):
    __tablename__ = "search_profiles"
    __table_args__ = (UniqueConstraint("user_id", "seed_key", name="uq_search_profile_seed"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    seed_key: Mapped[str | None] = mapped_column(String(50))
    archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchConfiguration(Base):
    __tablename__ = "search_configurations"
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    criteria: Mapped[dict[str, object]] = mapped_column(JSONB)


class SearchExecution(Base):
    __tablename__ = "search_executions"
    __table_args__ = (
        Index(
            "uq_search_active_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING','RUNNING')"),
        ),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','PARTIAL',"
            "'FAILED','CANCELLED','TIMED_OUT')",
            name="ck_search_execution_status",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("search_profiles.id"), index=True)
    profile_name: Mapped[str] = mapped_column(String(100))
    criteria: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    scope: Mapped[str] = mapped_column(String(30), default="IMPORTED_OFFERS")
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    reason: Mapped[str | None] = mapped_column(String(100))


class SearchTask(Base):
    __tablename__ = "search_tasks"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    stage: Mapped[str] = mapped_column(String(20), default="SCAN")
    cursor: Mapped[int] = mapped_column(default=0)
    attempt: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_token: Mapped[UUID | None] = mapped_column()
    locked_by: Mapped[str | None] = mapped_column(String(100))
    snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class SourceExecutionLog(Base):
    __tablename__ = "source_execution_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"))
    source_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="SKIPPED")
    reason: Mapped[str] = mapped_column(String(100), default="MANUAL_ONLY")


class SearchResult(Base):
    __tablename__ = "search_results"
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[UUID] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column()
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)


class CollectionPlan(Base):
    __tablename__ = "search_collection_plans"
    __table_args__ = (CheckConstraint("max_results BETWEEN 1 AND 500", name="ck_collection_max"),)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(default=1)
    max_results: Mapped[int] = mapped_column(default=10)
    sources: Mapped[dict[str, object]] = mapped_column(JSONB)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CollectionCheckpoint(Base):
    __tablename__ = "search_collection_checkpoints"
    __table_args__ = (
        UniqueConstraint("execution_id", "source_id", name="uq_collection_checkpoint"),
        CheckConstraint("page_index >= 0 AND collected >= 0", name="ck_collection_progress"),
        CheckConstraint(
            "created >= 0 AND existing >= 0 AND invalid >= 0", name="ck_collection_counts"
        ),
        CheckConstraint(
            "state IN ('PENDING','RUNNING','PARTIAL','SUCCEEDED')",
            name="ck_collection_source_state",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_executions.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"))
    state: Mapped[str] = mapped_column(String(20), default="PENDING")
    cursor: Mapped[str | None] = mapped_column(String(2048))
    seen_cursors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    page_index: Mapped[int] = mapped_column(default=0)
    collected: Mapped[int] = mapped_column(default=0)
    created: Mapped[int] = mapped_column(default=0)
    existing: Mapped[int] = mapped_column(default=0)
    invalid: Mapped[int] = mapped_column(default=0)
    source_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    query_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(100))
