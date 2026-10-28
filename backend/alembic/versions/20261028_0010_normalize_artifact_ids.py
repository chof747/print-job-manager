"""Normalize legacy sha256-prefixed artifact identifiers.

Revision ID: 20261028_0010
Revises: 20261028_0009
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0010"
down_revision = "20261028_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legacy_artifact_identifiers",
        sa.Column("legacy_id", sa.String(255), primary_key=True),
        sa.Column("artifact_id", sa.String(255), nullable=False, unique=True),
        sa.Column("storage_key_converted", sa.Boolean(), nullable=False),
    )
    # Only canonical legacy identifiers whose embedded digest agrees with the
    # stored digest are safe to convert. A collision fails the transaction.
    op.execute("""
        INSERT INTO legacy_artifact_identifiers (legacy_id, artifact_id, storage_key_converted)
        SELECT id, sha256, storage_key = id FROM artifacts
        WHERE id = 'sha256:' || sha256 AND sha256 ~ '^[0-9a-f]{64}$'
    """)
    op.drop_constraint("jobs_artifact_ref_fkey", "jobs", type_="foreignkey")
    op.execute("""
        UPDATE jobs SET artifact_ref = mapping.artifact_id
        FROM legacy_artifact_identifiers AS mapping
        WHERE jobs.artifact_ref = mapping.legacy_id
    """)
    op.execute("""
        UPDATE artifacts SET id = mapping.artifact_id,
            storage_key = CASE WHEN mapping.storage_key_converted THEN mapping.artifact_id ELSE artifacts.storage_key END
        FROM legacy_artifact_identifiers AS mapping WHERE artifacts.id = mapping.legacy_id
    """)
    op.create_foreign_key(
        "jobs_artifact_ref_fkey", "jobs", "artifacts", ["artifact_ref"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("jobs_artifact_ref_fkey", "jobs", type_="foreignkey")
    op.execute("""
        UPDATE jobs SET artifact_ref = mapping.legacy_id
        FROM legacy_artifact_identifiers AS mapping
        WHERE jobs.artifact_ref = mapping.artifact_id
    """)
    op.execute("""
        UPDATE artifacts SET id = mapping.legacy_id,
            storage_key = CASE WHEN mapping.storage_key_converted AND artifacts.storage_key = mapping.artifact_id
                THEN mapping.legacy_id ELSE artifacts.storage_key END
        FROM legacy_artifact_identifiers AS mapping WHERE artifacts.id = mapping.artifact_id
    """)
    op.create_foreign_key(
        "jobs_artifact_ref_fkey", "jobs", "artifacts", ["artifact_ref"], ["id"]
    )
    op.drop_table("legacy_artifact_identifiers")
