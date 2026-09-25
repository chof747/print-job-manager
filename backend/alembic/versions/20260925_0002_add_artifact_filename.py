"""add artifact filename

Revision ID: 20260925_0002
Revises: 20260902_0001
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "20260925_0002"
down_revision = "20260902_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("artifacts", "filename")
