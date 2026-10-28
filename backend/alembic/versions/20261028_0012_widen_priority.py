"""Widen priorities on databases upgraded before the backfill fix.

Revision ID: 20261028_0012
Revises: 20261028_0011
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0012"
down_revision = "20261028_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("jobs", "priority", type_=sa.Numeric(), existing_nullable=False)


def downgrade() -> None:
    # Revision 0005 also uses numeric; narrowing would lose valid priorities.
    pass
