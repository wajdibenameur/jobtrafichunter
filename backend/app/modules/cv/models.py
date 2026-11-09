from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
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


class CvDocument(Base):
    __tablename__ = "cv_documents"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_cv_document_owner"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(20), default="READY")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CvVersion(Base):
    __tablename__ = "cv_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "number", name="uq_cv_version_number"),
        UniqueConstraint("id", "user_id", name="uq_cv_version_owner"),
        ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["cv_documents.id", "cv_documents.user_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("byte_size > 0 AND byte_size <= 5242880", name="ck_cv_version_size"),
        CheckConstraint(
            "state IN ('PUBLISHING','READY','DELETING','FAILED')", name="ck_cv_version_state"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(index=True)
    document_id: Mapped[UUID] = mapped_column(index=True)
    number: Mapped[int] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), default="PUBLISHING")
    byte_size: Mapped[int] = mapped_column()
    # Filename, extracted text and inspection are never plaintext in PostgreSQL.
    private_payload: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActiveCv(Base):
    __tablename__ = "active_cvs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["version_id", "user_id"], ["cv_versions.id", "cv_versions.user_id"], ondelete="CASCADE"
        ),
    )
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    version_id: Mapped[UUID] = mapped_column(unique=True)


class CvAudit(Base):
    __tablename__ = "cv_audit"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[UUID] = mapped_column()
    version_id: Mapped[UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CvStorageIntent(Base):
    __tablename__ = "cv_storage_intents"
    __table_args__ = (UniqueConstraint("version_id", "kind", name="uq_cv_storage_intent"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[UUID] = mapped_column()
    version_id: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(20))
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
