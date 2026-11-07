"""Persist the job hardened nozzle requirement.

Revision ID: 20261105_0042
Revises: 20261105_0041
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0042"
down_revision = "20261105_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("execution_requires_hardened_nozzle", sa.Boolean()))


def downgrade() -> None:
    op.drop_column("jobs", "execution_requires_hardened_nozzle")
