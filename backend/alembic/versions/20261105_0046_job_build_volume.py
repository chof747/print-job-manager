"""Persist declared job build-volume requirements.

Revision ID: 20261105_0046
Revises: 20261105_0045
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0046"
down_revision = "20261105_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for axis in ("x", "y", "z"):
        op.add_column("jobs", sa.Column(f"requirement_build_volume_{axis}", sa.Float()))


def downgrade() -> None:
    for axis in ("z", "y", "x"):
        op.drop_column("jobs", f"requirement_build_volume_{axis}")
