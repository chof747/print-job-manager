"""Persist the hardened nozzle printer capability.

Revision ID: 20261105_0044
Revises: 20261105_0043
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0044"
down_revision = "20261105_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("printer_capabilities", sa.Column("hardened_nozzle", sa.Boolean()))


def downgrade() -> None:
    op.drop_column("printer_capabilities", "hardened_nozzle")
