"""Backfill typed job material from legacy execution data.

Revision ID: 20261028_0006
Revises: 20261028_0005
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0006"
down_revision = "20261028_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("material", sa.Text(), nullable=True))
    op.execute("""
        UPDATE jobs SET material = node.text_value
        FROM job_data_nodes AS node
        WHERE node.owner_id = jobs.id AND node.field = 'execution'
          AND node.path = '/material' AND node.kind = 'string'
    """)


def downgrade() -> None:
    op.drop_column("jobs", "material")
