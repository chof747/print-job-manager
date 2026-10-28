"""Store imported filament weight as a numeric artifact fact.

Revision ID: 20261028_0008
Revises: 20261028_0007
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0008"
down_revision = "20261028_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifacts", sa.Column("filament_weight_grams", sa.Float(), nullable=True)
    )
    op.execute("""
        UPDATE artifacts SET filament_weight_grams = node.text_value::double precision
        FROM artifact_data_nodes AS node
        WHERE node.owner_id = artifacts.id AND node.field = 'metadata'
          AND node.path = '/extractedMetadata/filamentWeightGrams'
          AND node.kind IN ('integer', 'float')
    """)


def downgrade() -> None:
    op.drop_column("artifacts", "filament_weight_grams")
