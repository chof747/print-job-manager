"""Persist the job enclosure requirement.

Revision ID: 20261105_0039
Revises: 20261028_0040
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0039"
down_revision = "20261028_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("execution_requires_enclosure", sa.Boolean()))


def downgrade() -> None:
    op.drop_column("jobs", "execution_requires_enclosure")
