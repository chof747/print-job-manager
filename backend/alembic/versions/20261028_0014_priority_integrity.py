"""Require finite integer-valued priorities without narrowing their range.

Revision ID: 20261028_0014
Revises: 20261028_0013
"""

from alembic import op

revision = "20261028_0014"
down_revision = "20261028_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_jobs_priority_integer",
        "jobs",
        "priority = trunc(priority) AND priority > '-Infinity'::numeric AND priority < 'Infinity'::numeric",
    )


def downgrade() -> None:
    op.drop_constraint("ck_jobs_priority_integer", "jobs", type_="check")
