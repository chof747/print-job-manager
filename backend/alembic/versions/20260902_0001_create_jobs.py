"""create jobs

Revision ID: 20260902_0001
Revises:
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260902_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column(
            "parsed_metadata_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("artifact_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "parsed_metadata_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "execution_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "scheduling_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "queue_position",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            unique=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_ref"),
        sa.ForeignKeyConstraint(["artifact_ref"], ["artifacts.id"]),
    )
    op.create_index("ix_jobs_state", "jobs", ["state"])
    op.create_table(
        "job_history",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )


def downgrade() -> None:
    op.drop_table("job_history")
    op.drop_index("ix_jobs_state", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("artifacts")
