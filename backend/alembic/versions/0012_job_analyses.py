"""Add private local matching preview tables."""

import sqlalchemy as sa

from alembic import op

revision = "0012_job_analyses"
down_revision = "0011_collection_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=50), nullable=False),
        sa.Column("private_payload", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "cache_key", name="uq_job_analysis_cache"),
    )
    op.create_index(op.f("ix_job_analyses_user_id"), "job_analyses", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("job_analyses")
