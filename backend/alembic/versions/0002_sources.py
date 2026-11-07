"""Source catalogue and owner preferences; manual workflows only."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_sources"
down_revision: str | None = "0001_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = op.create_table(
        "job_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="CASCADE")),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("homepage", sa.String(4096), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("integration_type", sa.String(20), nullable=False),
        sa.Column("legal_status", sa.String(20), nullable=False),
        sa.Column("search_strategy", sa.String(30), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("verification", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "integration_type IN ('API','FEED','EMAIL_ALERT',"
            "'LINK_ONLY','MANUAL_IMPORT','DISABLED')",
            name="ck_source_integration",
        ),
        sa.CheckConstraint(
            "legal_status IN ('PERMITTED','LINK_ONLY','MANUAL_ONLY','UNVERIFIED')",
            name="ck_source_legal",
        ),
    )
    op.create_index("ix_job_sources_user_id", "job_sources", ["user_id"])
    op.create_table(
        "source_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("job_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("user_id", "source_id", name="uq_source_preference_owner"),
    )
    op.create_index("ix_source_preferences_user_id", "source_preferences", ["user_id"])
    op.create_index("ix_source_preferences_source_id", "source_preferences", ["source_id"])
    # Snapshot seed data: intentionally independent of mutable application imports.
    from datetime import UTC, datetime

    now = datetime(2026, 11, 7, tzinfo=UTC)
    seeds = [
        (
            "10000000-0000-4000-8000-000000000001",
            "linkedin",
            "LinkedIn",
            "https://www.linkedin.com/jobs/search/",
            "GLOBAL",
            "linkedin",
        ),
        (
            "10000000-0000-4000-8000-000000000002",
            "indeed",
            "Indeed",
            "https://www.indeed.com/jobs",
            "GLOBAL",
            "indeed",
        ),
        (
            "10000000-0000-4000-8000-000000000003",
            "keejob",
            "Keejob",
            "https://www.keejob.com/",
            "TN",
            "keejob",
        ),
        (
            "10000000-0000-4000-8000-000000000004",
            "tanitjobs",
            "Tanitjobs",
            "https://www.tanitjobs.com/",
            "TN",
            "tanitjobs",
        ),
    ]
    op.bulk_insert(
        table,
        [
            dict(
                id=UUID(identifier),
                user_id=None,
                slug=slug,
                name=name,
                homepage=homepage,
                region=region,
                integration_type="LINK_ONLY",
                legal_status="LINK_ONLY",
                search_strategy=strategy,
                archived=False,
                verification={},
                created_at=now,
            )
            for identifier, slug, name, homepage, region, strategy in seeds
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_source_preferences_source_id", table_name="source_preferences")
    op.drop_index("ix_source_preferences_user_id", table_name="source_preferences")
    op.drop_table("source_preferences")
    op.drop_index("ix_job_sources_user_id", table_name="job_sources")
    op.drop_table("job_sources")
