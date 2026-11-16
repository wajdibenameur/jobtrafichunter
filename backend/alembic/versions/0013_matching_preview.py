"""Add private local matching preview tables."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013_matching_preview"
down_revision = "0012_job_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scoring_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "config_hash", name="uq_scoring_policy_hash"),
        sa.UniqueConstraint("user_id", "version", name="uq_scoring_policy_version"),
    )
    op.create_index(
        op.f("ix_scoring_policies_user_id"), "scoring_policies", ["user_id"], unique=False
    )
    op.create_table(
        "matching_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("source_execution_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("cv_version_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_revision", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("private_snapshot", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "cursor >= 0 AND total >= 0 AND cache_hits >= 0", name="ck_matching_counts"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profile_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["cv_version_id"], ["cv_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["search_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["scoring_policies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_execution_id"], ["search_executions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id"),
    )
    op.create_index(
        op.f("ix_matching_runs_candidate_id"), "matching_runs", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_matching_runs_cv_version_id"), "matching_runs", ["cv_version_id"], unique=False
    )
    op.create_index(op.f("ix_matching_runs_user_id"), "matching_runs", ["user_id"], unique=False)
    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("private_payload", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_match_score"),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["job_analyses.id"],
        ),
        sa.ForeignKeyConstraint(["run_id"], ["matching_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "group_id", name="uq_match_run_group"),
    )
    op.create_index(op.f("ix_job_matches_cache_key"), "job_matches", ["cache_key"], unique=False)
    op.create_index(op.f("ix_job_matches_run_id"), "job_matches", ["run_id"], unique=False)
    op.create_index(op.f("ix_job_matches_user_id"), "job_matches", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("job_matches")
    op.drop_table("matching_runs")
    op.drop_table("scoring_policies")
