"""add job scheduling version

Revision ID: 20261028_0040
Revises: 20261028_0039
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0040"
down_revision = "20261028_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_scheduling",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("job_scheduling", "version", server_default=None)


def downgrade() -> None:
    op.drop_column("job_scheduling", "version")
