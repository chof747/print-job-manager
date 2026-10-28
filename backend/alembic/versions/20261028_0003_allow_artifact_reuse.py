"""allow multiple jobs per artifact

Revision ID: 20261028_0003
Revises: 20260925_0002
"""

from alembic import op

revision = "20261028_0003"
down_revision = "20260925_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("jobs_artifact_ref_key", "jobs", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("jobs_artifact_ref_key", "jobs", ["artifact_ref"])
