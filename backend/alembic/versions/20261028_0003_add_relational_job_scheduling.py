"""add relational job scheduling

Revision ID: 20261028_0039
Revises: 20261028_0038
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0039"
down_revision = "20261028_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_scheduling",
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Numeric(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("printer_assignment_mode", sa.String(length=32), nullable=True),
        sa.Column("preferred_printer_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_table(
        "job_scheduling_tags",
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("tag", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_scheduling.job_id"]),
        sa.PrimaryKeyConstraint("job_id", "tag"),
    )
    op.execute("INSERT INTO job_scheduling (job_id, priority) SELECT id, priority FROM jobs")


def downgrade() -> None:
    op.execute("UPDATE jobs SET priority = scheduling.priority FROM job_scheduling AS scheduling WHERE jobs.id = scheduling.job_id")
    op.drop_table("job_scheduling_tags")
    op.drop_table("job_scheduling")
