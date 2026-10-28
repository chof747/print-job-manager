"""add relational job scheduling

Revision ID: 20261028_0003
Revises: 20260925_0002
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0003"
down_revision = "20260925_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_scheduling",
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
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
    op.execute(
        """
        INSERT INTO job_scheduling (
            job_id, priority, due_date, notes, printer_assignment_mode, preferred_printer_id
        )
        SELECT
            id,
            COALESCE((scheduling_data ->> 'priority')::integer, 0),
            NULLIF(scheduling_data ->> 'dueDate', '')::date,
            scheduling_data ->> 'notes',
            scheduling_data -> 'printerAssignment' ->> 'mode',
            scheduling_data -> 'printerAssignment' ->> 'printerId'
        FROM jobs
        """
    )
    op.execute(
        """
        INSERT INTO job_scheduling_tags (job_id, tag, position)
        SELECT jobs.id, tags.tag, tags.position - 1
        FROM jobs
        CROSS JOIN LATERAL jsonb_array_elements_text(
            COALESCE(scheduling_data -> 'tags', '[]'::jsonb)
        ) WITH ORDINALITY AS tags(tag, position)
        """
    )


def downgrade() -> None:
    op.drop_table("job_scheduling_tags")
    op.drop_table("job_scheduling")
