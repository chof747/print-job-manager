"""Persist printer nozzle diameter and build volume.

Revision ID: 20261105_0045
Revises: 20261105_0044
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0045"
down_revision = "20261105_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("nozzle_diameter", "build_volume_x", "build_volume_y", "build_volume_z"):
        op.add_column("printer_capabilities", sa.Column(name, sa.Float()))


def downgrade() -> None:
    for name in ("build_volume_z", "build_volume_y", "build_volume_x", "nozzle_diameter"):
        op.drop_column("printer_capabilities", name)
