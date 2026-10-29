"""Widen duration columns on databases upgraded before the backfill fix.

Revision ID: 20261028_0011
Revises: 20261028_0010
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0011"
down_revision = "20261028_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("artifacts", "estimated_duration"),
        ("artifacts", "snapshot_duration"),
        ("jobs", "snapshot_duration"),
        ("jobs", "execution_duration"),
    ):
        op.alter_column(
            table, column, type_=sa.Numeric(), postgresql_using=f"{column}::numeric"
        )


def downgrade() -> None:
    # Earlier revisions now also use numeric so no narrowing or data loss is needed.
    pass
