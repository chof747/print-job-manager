"""Store imported estimated duration as a numeric artifact fact.

Revision ID: 20261028_0007
Revises: 20261028_0006
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0007"
down_revision = "20261028_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifacts", sa.Column("estimated_duration", sa.Numeric(), nullable=True)
    )
    op.execute("""
        UPDATE artifacts SET estimated_duration = node.text_value::numeric
        FROM artifact_data_nodes AS node
        WHERE node.owner_id = artifacts.id AND node.field = 'metadata'
          AND node.path = '/extractedMetadata/estimatedDuration' AND node.kind = 'integer'
    """)


def downgrade() -> None:
    op.drop_column("artifacts", "estimated_duration")
