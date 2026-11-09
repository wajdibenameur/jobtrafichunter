from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.shared.clock import utcnow


class JobSource(Base):
    __tablename__ = "job_sources"
    __table_args__ = (
        CheckConstraint(
            "integration_type IN ('API','FEED','EMAIL_ALERT',"
            "'LINK_ONLY','MANUAL_IMPORT','DISABLED')",
            name="ck_source_integration",
        ),
        CheckConstraint(
            "legal_status IN ('PERMITTED','LINK_ONLY','MANUAL_ONLY','UNVERIFIED')",
            name="ck_source_legal",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    homepage: Mapped[str] = mapped_column(String(4096))
    region: Mapped[str] = mapped_column(String(20), default="GLOBAL")
    integration_type: Mapped[str] = mapped_column(String(20), default="LINK_ONLY")
    legal_status: Mapped[str] = mapped_column(String(20), default="UNVERIFIED")
    search_strategy: Mapped[str] = mapped_column(String(30), default="homepage")
    archived: Mapped[bool] = mapped_column(default=False)
    verification: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourcePreference(Base):
    __tablename__ = "source_preferences"
    __table_args__ = (UniqueConstraint("user_id", "source_id", name="uq_source_preference_owner"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_sources.id", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(default=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class CollectionConfig(Base):
    __tablename__ = "source_collection_configs"
    __table_args__ = (CheckConstraint("version > 0", name="ck_collection_config_version"),)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"), primary_key=True)
    adapter_key: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(default=1)
    enabled: Mapped[bool] = mapped_column(default=False)
    routes: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    limits: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class CollectionRuntime(Base):
    __tablename__ = "source_collection_runtime"
    __table_args__ = (CheckConstraint("failures >= 0", name="ck_collection_failures"),)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"), primary_key=True)
    next_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deferred_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active_reservation_id: Mapped[UUID | None]
    failures: Mapped[int] = mapped_column(default=0)
    disabled_reason: Mapped[str | None] = mapped_column(String(100))


class CollectionReservation(Base):
    __tablename__ = "source_collection_reservations"
    __table_args__ = (
        UniqueConstraint("execution_id", "source_id", "ordinal", name="uq_collection_http_attempt"),
        CheckConstraint("wire_bytes >= 0 AND body_bytes >= 0", name="ck_collection_http_bytes"),
        CheckConstraint("ordinal >= 0", name="ck_collection_http_ordinal"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("job_sources.id"), index=True)
    execution_id: Mapped[UUID] = mapped_column(index=True)
    checkpoint_id: Mapped[UUID] = mapped_column()
    request_key: Mapped[str] = mapped_column(String(64))
    ordinal: Mapped[int]
    wire_bytes: Mapped[int]
    body_bytes: Mapped[int]
    settled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
