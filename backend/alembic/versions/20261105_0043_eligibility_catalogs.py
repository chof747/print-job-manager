"""Persist printer capabilities and material inventory.

Revision ID: 20261105_0043
Revises: 20261105_0042
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0043"
down_revision = "20261105_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "printer_capabilities",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("enclosure", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "inventory_materials",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("material_type", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("amount_grams", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("inventory_materials")
    op.drop_table("printer_capabilities")
