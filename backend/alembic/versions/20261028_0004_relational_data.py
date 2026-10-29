"""Move structured job and artifact data into relational nodes.

Revision ID: 20261028_0004
Revises: 20261028_0003
"""

import json
from typing import Protocol

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261028_0004"
down_revision = "20261028_0003"
branch_labels = None
depends_on = None

FIELDS = {
    "artifacts": {"parsed_metadata_snapshot": "metadata"},
    "jobs": {
        "parsed_metadata_snapshot": "metadata",
        "execution_data": "execution",
        "scheduling_data": "scheduling",
    },
}


# Frozen conversion for this revision's node representation.
class DataNode(Protocol):
    field: str
    path: str
    kind: str
    text_value: str | None
    bool_value: bool | None


def encode(value: object, field: str, path: str = "") -> list[dict[str, object]]:
    row: dict[str, object] = {"field": field, "path": path, "kind": "null"}
    children: list[dict[str, object]] = []
    if isinstance(value, dict):
        row["kind"] = "object"
        for key, item in value.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            children.extend(encode(item, field, path + "/" + escaped))
    elif isinstance(value, list):
        row["kind"] = "array"
        for index, item in enumerate(value):
            children.extend(encode(item, field, path + "/" + str(index)))
    elif isinstance(value, bool):
        row.update(kind="boolean", bool_value=value)
    elif isinstance(value, int):
        row.update(kind="integer", text_value=str(value))
    elif isinstance(value, float):
        row.update(kind="float", text_value=repr(value))
    elif isinstance(value, str):
        row.update(kind="string", text_value=value)
    elif value is not None:
        raise TypeError(f"Unsupported value: {type(value).__name__}")
    return [row, *children]


def decode(rows: list[DataNode], field: str) -> object:
    values = {row.path: row for row in rows if row.field == field}

    def visit(path: str) -> object:
        row = values[path]
        if row.kind in ("object", "array"):
            prefix = path + "/"
            children = [
                (p[len(prefix) :], p)
                for p in values
                if p.startswith(prefix) and "/" not in p[len(prefix) :]
            ]
            if row.kind == "array":
                return [
                    visit(p) for _, p in sorted(children, key=lambda pair: int(pair[0]))
                ]
            return {
                key.replace("~1", "/").replace("~0", "~"): visit(p)
                for key, p in children
            }
        if row.kind == "null":
            return None
        if row.kind == "boolean":
            return row.bool_value
        if row.kind == "integer":
            assert row.text_value is not None
            return int(row.text_value)
        if row.kind == "float":
            assert row.text_value is not None
            return float(row.text_value)
        return row.text_value

    return visit("")


def upgrade() -> None:
    connection = op.get_bind()
    for table, fields in FIELDS.items():
        nodes = "artifact_data_nodes" if table == "artifacts" else "job_data_nodes"
        op.create_table(
            nodes,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "owner_id",
                sa.String(255),
                sa.ForeignKey(f"{table}.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("field", sa.String(32), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("text_value", sa.Text()),
            sa.Column("bool_value", sa.Boolean()),
        )
        rows = connection.execute(
            sa.text(f"SELECT id, {', '.join(fields)} FROM {table}")
        ).mappings()
        for row in rows:
            for column, field in fields.items():
                for node in encode(row[column], field):
                    connection.execute(
                        sa.text(
                            f"INSERT INTO {nodes} (owner_id, field, path, kind, text_value, bool_value) VALUES (:owner_id, :field, :path, :kind, :text_value, :bool_value)"
                        ),
                        {
                            "owner_id": row["id"],
                            "text_value": None,
                            "bool_value": None,
                            **node,
                        },
                    )
        for column in fields:
            op.drop_column(table, column)


def downgrade() -> None:
    connection = op.get_bind()
    for table, fields in FIELDS.items():
        nodes = "artifact_data_nodes" if table == "artifacts" else "job_data_nodes"
        for column in fields:
            op.add_column(table, sa.Column(column, postgresql.JSONB(), nullable=True))
        for owner in connection.execute(sa.text(f"SELECT id FROM {table}")):
            rows = connection.execute(
                sa.text(
                    f"SELECT field, path, kind, text_value, bool_value FROM {nodes} WHERE owner_id = :id"
                ),
                {"id": owner.id},
            ).all()
            for column, field in fields.items():
                connection.execute(
                    sa.text(
                        f"UPDATE {table} SET {column} = CAST(:value AS jsonb) WHERE id = :id"
                    ),
                    {"id": owner.id, "value": json.dumps(decode(rows, field))},
                )
        for column in fields:
            op.alter_column(table, column, nullable=False)
        op.drop_table(nodes)
