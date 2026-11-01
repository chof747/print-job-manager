"""Store job priority as a typed integer.

Revision ID: 20261028_0005
Revises: 20261028_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0005"
down_revision = "20261028_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid = connection.execute(
        sa.text("""
            SELECT owner_id FROM job_data_nodes
            WHERE field = 'scheduling' AND (path = '/priority' OR path LIKE '/priority/%')
            GROUP BY owner_id
            HAVING count(*) <> 1 OR bool_or(
                path <> '/priority' OR kind <> 'integer' OR text_value IS NULL
                OR text_value !~ '^-?[0-9]+$' OR bool_value IS NOT NULL
            )
            LIMIT 1
        """)
    ).scalar_one_or_none()
    if invalid is not None:
        raise ValueError(f"Unsupported legacy priority for job {invalid}")
    op.add_column(
        "jobs", sa.Column("priority", sa.Numeric(), nullable=False, server_default="0")
    )
    op.execute("""
        UPDATE jobs SET priority = node.text_value::numeric
        FROM job_data_nodes AS node
        WHERE node.owner_id = jobs.id AND node.field = 'scheduling'
          AND node.path = '/priority' AND node.kind = 'integer'
    """)
    op.execute(
        "DELETE FROM job_data_nodes WHERE field = 'scheduling' AND path = '/priority'"
    )


def downgrade() -> None:
    op.execute("""
        INSERT INTO job_data_nodes (owner_id, field, path, kind, text_value)
        SELECT id, 'scheduling', '/priority', 'integer', priority::text FROM jobs
    """)
    op.drop_column("jobs", "priority")
