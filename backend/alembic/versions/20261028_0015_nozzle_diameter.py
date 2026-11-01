"""Add the nozzle diameter fact to already-migrated databases.

Revision ID: 20261028_0015
Revises: 20261028_0014
"""

from alembic import op

revision = "20261028_0015"
down_revision = "20261028_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS nozzle_diameter double precision"
    )


def downgrade() -> None:
    # Revision 0009 owns this column when migrating from the beginning.
    pass
