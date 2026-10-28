"""Widen priorities for databases already at the bigint revision.

Revision ID: 20261028_0013
Revises: 20261028_0012
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0013"
down_revision = "20261028_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("jobs", "priority", type_=sa.Numeric(), existing_nullable=False)


def downgrade() -> None:
    # Earlier revisions also use numeric; do not discard large priorities.
    pass
