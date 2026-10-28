"""Add typed scalar planning facts to existing databases.

Revision ID: 20261028_0016
Revises: 20261028_0015
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0016"
down_revision = "20261028_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("job_planning_facts"):
        return
    op.create_table(
        "job_planning_facts",
        sa.Column(
            "job_id",
            sa.String(255),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("text_value", sa.Text()),
        sa.Column("integer_value", sa.Numeric()),
        sa.Column("float_value", sa.Float()),
        sa.Column("boolean_value", sa.Boolean()),
        sa.CheckConstraint(
            "num_nonnulls(text_value, integer_value, float_value, boolean_value) <= 1",
            name="ck_planning_one_value",
        ),
        sa.CheckConstraint(
            "integer_value IS NULL OR (integer_value = trunc(integer_value) AND integer_value > '-Infinity'::numeric AND integer_value < 'Infinity'::numeric)",
            name="ck_planning_integer",
        ),
    )


def downgrade() -> None:
    # Revision 0009 owns the relation; it restores facts before dropping it.
    pass
