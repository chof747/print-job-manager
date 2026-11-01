"""add job scheduling version

Revision ID: 20261028_0004
Revises: 20261028_0003
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0004"
down_revision = "20261028_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_scheduling",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE job_scheduling AS scheduling
        SET version = COALESCE((jobs.scheduling_data ->> '_schedulingVersion')::integer, 0)
        FROM jobs WHERE jobs.id = scheduling.job_id
        """
    )
    op.execute("UPDATE jobs SET scheduling_data = scheduling_data - '_schedulingVersion'")
    op.alter_column("job_scheduling", "version", server_default=None)


def downgrade() -> None:
    op.execute(
        """
        UPDATE jobs
        SET scheduling_data = scheduling_data || jsonb_build_object(
            '_schedulingVersion', scheduling.version
        )
        FROM job_scheduling AS scheduling
        WHERE jobs.id = scheduling.job_id
        """
    )
    op.drop_column("job_scheduling", "version")
