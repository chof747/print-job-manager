"""Persist material attributes required by a job.

Revision ID: 20261105_0041
Revises: 20261105_0039
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0041"
down_revision = "20261105_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("execution_material_color", sa.Text()))
    op.add_column("jobs", sa.Column("execution_material_amount_grams", sa.Float()))


def downgrade() -> None:
    op.drop_column("jobs", "execution_material_amount_grams")
    op.drop_column("jobs", "execution_material_color")
