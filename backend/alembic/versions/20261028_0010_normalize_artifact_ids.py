"""Normalize legacy sha256-prefixed artifact identifiers.

Revision ID: 20261028_0010
Revises: 20261028_0009
"""

from alembic import op

revision = "20261028_0010"
down_revision = "20261028_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only canonical legacy identifiers whose embedded digest agrees with the
    # stored digest are safe to convert. A collision fails the transaction.
    op.drop_constraint("jobs_artifact_ref_fkey", "jobs", type_="foreignkey")
    op.execute("""
        UPDATE jobs SET artifact_ref = artifacts.sha256
        FROM artifacts
        WHERE jobs.artifact_ref = artifacts.id
          AND artifacts.id = 'sha256:' || artifacts.sha256
          AND artifacts.sha256 ~ '^[0-9a-f]{64}$'
    """)
    op.execute("""
        UPDATE artifacts SET id = sha256,
            storage_key = CASE WHEN storage_key = id THEN sha256 ELSE storage_key END
        WHERE id = 'sha256:' || sha256 AND sha256 ~ '^[0-9a-f]{64}$'
    """)
    op.create_foreign_key(
        "jobs_artifact_ref_fkey", "jobs", "artifacts", ["artifact_ref"], ["id"]
    )


def downgrade() -> None:
    # The old identifiers are intentionally not retained for disposable test data.
    pass
