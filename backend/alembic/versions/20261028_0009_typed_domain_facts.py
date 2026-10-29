"""Replace generic nodes with typed import and job facts.

Revision ID: 20261028_0009
Revises: 20261028_0008
"""

from datetime import datetime
from typing import Protocol

import sqlalchemy as sa
from alembic import op
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import TypeDecorator

revision = "20261028_0009"
down_revision = "20261028_0008"
branch_labels = None
depends_on = None

# Frozen revision-local models and node conversion. Do not import application models here.


class Base(DeclarativeBase):
    pass


class NumericInteger(TypeDecorator):
    """Unbounded PostgreSQL numeric stored and returned as Python integers."""

    impl = Numeric
    cache_ok = True

    def process_result_value(self, value, dialect):
        return int(value) if value is not None else None


class SnapshotFacts:
    snapshot_has_extracted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    snapshot_has_provenance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    snapshot_material: Mapped[str | None] = mapped_column(Text)
    snapshot_duration: Mapped[int | None] = mapped_column(NumericInteger())
    snapshot_weight: Mapped[float | None] = mapped_column(Float)
    missing_values: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    diagnostic_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    diagnostic_sources: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    material_parser: Mapped[str | None] = mapped_column(Text)
    material_source: Mapped[str | None] = mapped_column(Text)
    duration_parser: Mapped[str | None] = mapped_column(Text)
    duration_source: Mapped[str | None] = mapped_column(Text)
    weight_parser: Mapped[str | None] = mapped_column(Text)
    weight_source: Mapped[str | None] = mapped_column(Text)

    @property
    def parsed_metadata_snapshot(self):
        result = {
            "missingPlanningValues": list(self.missing_values),
            "diagnostics": [
                {"code": code, "sourceKey": source}
                for code, source in zip(
                    self.diagnostic_codes, self.diagnostic_sources, strict=True
                )
            ],
        }
        if self.snapshot_has_extracted:
            result["extractedMetadata"] = {
                key: value
                for key, value in (
                    ("material", self.snapshot_material),
                    ("estimatedDuration", self.snapshot_duration),
                    ("filamentWeightGrams", self.snapshot_weight),
                )
                if value is not None
            }
        if self.snapshot_has_provenance:
            result["provenance"] = {
                key: {"parser": parser, "sourceKey": source}
                for key, parser, source in (
                    ("material", self.material_parser, self.material_source),
                    ("estimatedDuration", self.duration_parser, self.duration_source),
                    ("filamentWeightGrams", self.weight_parser, self.weight_source),
                )
                if parser is not None
            }
        return result

    @parsed_metadata_snapshot.setter
    def parsed_metadata_snapshot(self, value):
        self._set_snapshot(value)

    def _set_snapshot(self, value):
        _keys(
            value,
            {"missingPlanningValues", "diagnostics", "extractedMetadata", "provenance"},
        )
        self.missing_values = value["missingPlanningValues"]
        diagnostics = value["diagnostics"]
        for diagnostic in diagnostics:
            _keys(diagnostic, {"code", "sourceKey"}, required=True)
        self.diagnostic_codes = [d["code"] for d in diagnostics]
        self.diagnostic_sources = [d["sourceKey"] for d in diagnostics]
        self.snapshot_has_extracted = "extractedMetadata" in value
        self.snapshot_has_provenance = "provenance" in value
        extracted = value.get("extractedMetadata", {})
        provenance = value.get("provenance", {})
        fields = {"material", "estimatedDuration", "filamentWeightGrams"}
        _keys(extracted, fields)
        _keys(provenance, fields)
        self.snapshot_material = extracted.get("material")
        self.snapshot_duration = extracted.get("estimatedDuration")
        self.snapshot_weight = extracted.get("filamentWeightGrams")
        for key, prefix in (
            ("material", "material"),
            ("estimatedDuration", "duration"),
            ("filamentWeightGrams", "weight"),
        ):
            item = provenance.get(key)
            if item is not None:
                _keys(item, {"parser", "sourceKey"}, required=True)
            setattr(self, prefix + "_parser", item["parser"] if item else None)
            setattr(self, prefix + "_source", item["sourceKey"] if item else None)


def _keys(value, allowed, required=False):
    if (
        not isinstance(value, dict)
        or set(value) - allowed
        or (required and set(value) != allowed)
    ):
        raise ValueError(
            "Unsupported persisted domain data; migration cannot safely discard it"
        )


class JobRecord(SnapshotFacts, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "priority = trunc(priority) AND priority > '-Infinity'::numeric AND priority < 'Infinity'::numeric",
            name="ck_jobs_priority_integer",
        ),
    )
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_ref: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(
        NumericInteger(), nullable=False, server_default="0"
    )
    material: Mapped[str | None] = mapped_column(Text)
    artifact_filename: Mapped[str | None] = mapped_column(Text)
    nozzle_diameter: Mapped[float | None] = mapped_column(Float)
    execution_has_artifact_ref: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    execution_has_material: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    execution_has_extracted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    execution_material: Mapped[str | None] = mapped_column(Text)
    execution_duration: Mapped[int | None] = mapped_column(NumericInteger())
    execution_weight: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    queue_position: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), unique=True, nullable=False
    )

    @property
    def execution_data(self):
        result = {}
        if self.execution_has_artifact_ref:
            result["artifactRef"] = self.artifact_ref
        if self.execution_has_material:
            result["material"] = self.material
        if self.artifact_filename is not None:
            result["artifactFilename"] = self.artifact_filename
        if self.nozzle_diameter is not None:
            result["nozzleDiameter"] = self.nozzle_diameter
        if self.execution_has_extracted:
            result["extractedMetadata"] = {
                key: value
                for key, value in (
                    ("material", self.execution_material),
                    ("estimatedDuration", self.execution_duration),
                    ("filamentWeightGrams", self.execution_weight),
                )
                if value is not None
            }
        return result

    @execution_data.setter
    def execution_data(self, value):
        if not isinstance(value, dict):
            raise TypeError("Execution data must be an object")
        self.execution_has_artifact_ref = "artifactRef" in value
        self.execution_has_material = "material" in value
        self.artifact_ref = value.get("artifactRef", self.artifact_ref)
        self.material = value.get("material")
        self.artifact_filename = value.get("artifactFilename")
        self.nozzle_diameter = value.get("nozzleDiameter")
        self.execution_has_extracted = "extractedMetadata" in value
        extracted = value.get("extractedMetadata", {})
        _keys(extracted, {"material", "estimatedDuration", "filamentWeightGrams"})
        self.execution_material = extracted.get("material")
        self.execution_duration = extracted.get("estimatedDuration")
        self.execution_weight = extracted.get("filamentWeightGrams")

    @property
    def scheduling_data(self):
        return {"priority": self.priority}

    @scheduling_data.setter
    def scheduling_data(self, value):
        _keys(value, {"priority"}, required=True)
        self.priority = value["priority"]


class JobHistoryRecord(Base):
    __tablename__ = "job_history"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("jobs.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArtifactRecord(SnapshotFacts, Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    estimated_duration: Mapped[int | None] = mapped_column(NumericInteger())
    filament_weight_grams: Mapped[float | None] = mapped_column(Float)

    @property
    def parsed_metadata_snapshot(self):
        return super().parsed_metadata_snapshot

    @parsed_metadata_snapshot.setter
    def parsed_metadata_snapshot(self, value):
        self._set_snapshot(value)
        self.estimated_duration = self.snapshot_duration
        self.filament_weight_grams = self.snapshot_weight


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


SNAPSHOT_COLUMNS = {
    "snapshot_has_extracted": sa.Boolean(),
    "snapshot_has_provenance": sa.Boolean(),
    "snapshot_material": sa.Text(),
    "snapshot_duration": sa.Numeric(),
    "snapshot_weight": sa.Float(),
    "missing_values": ARRAY(sa.Text()),
    "diagnostic_codes": ARRAY(sa.Text()),
    "diagnostic_sources": ARRAY(sa.Text()),
    "material_parser": sa.Text(),
    "material_source": sa.Text(),
    "duration_parser": sa.Text(),
    "duration_source": sa.Text(),
    "weight_parser": sa.Text(),
    "weight_source": sa.Text(),
}
JOB_COLUMNS = {
    "artifact_filename": sa.Text(),
    "nozzle_diameter": sa.Float(),
    "execution_has_extracted": sa.Boolean(),
    "execution_has_artifact_ref": sa.Boolean(),
    "execution_has_material": sa.Boolean(),
    "execution_material": sa.Text(),
    "execution_duration": sa.Numeric(),
    "execution_weight": sa.Float(),
}


def upgrade():
    connection = op.get_bind()
    for table in ("artifacts", "jobs"):
        for name, type_ in SNAPSHOT_COLUMNS.items():
            op.add_column(table, sa.Column(name, type_, nullable=True))
    for name, type_ in JOB_COLUMNS.items():
        op.add_column("jobs", sa.Column(name, type_, nullable=True))
    with Session(bind=connection) as session:
        for model, table in (
            (ArtifactRecord, "artifact_data_nodes"),
            (JobRecord, "job_data_nodes"),
        ):
            for record in session.scalars(sa.select(model)).all():
                nodes = connection.execute(
                    sa.text(
                        f"SELECT field, path, kind, text_value, bool_value FROM {table} WHERE owner_id = :id"
                    ),
                    {"id": record.id},
                ).all()
                snapshot = decode(nodes, "metadata")
                record.parsed_metadata_snapshot = snapshot
                if record.parsed_metadata_snapshot != snapshot:
                    raise ValueError(f"Cannot safely backfill metadata for {record.id}")
                if model is JobRecord:
                    execution = decode(nodes, "execution")
                    scheduling = decode(nodes, "scheduling")
                    # Unknown legacy planning data is disposable test data.
                    if isinstance(execution, dict):
                        execution = {
                            key: value
                            for key, value in execution.items()
                            if key
                            in {
                                "artifactRef",
                                "material",
                                "artifactFilename",
                                "extractedMetadata",
                                "nozzleDiameter",
                            }
                        }
                    record.execution_data = execution
                    if record.execution_data != execution or scheduling:
                        raise ValueError(
                            f"Cannot safely backfill job data for {record.id}"
                        )
            session.flush()
    for table in ("artifacts", "jobs"):
        for name in (
            "snapshot_has_extracted",
            "snapshot_has_provenance",
            "missing_values",
            "diagnostic_codes",
            "diagnostic_sources",
        ):
            op.alter_column(table, name, nullable=False)
    op.alter_column("jobs", "execution_has_extracted", nullable=False)
    op.alter_column("jobs", "execution_has_artifact_ref", nullable=False)
    op.alter_column("jobs", "execution_has_material", nullable=False)
    op.drop_table("job_data_nodes")
    op.drop_table("artifact_data_nodes")


def downgrade():
    connection = op.get_bind()
    for owner_table, node_table in (
        ("artifacts", "artifact_data_nodes"),
        ("jobs", "job_data_nodes"),
    ):
        op.create_table(
            node_table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "owner_id",
                sa.String(255),
                sa.ForeignKey(f"{owner_table}.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("field", sa.String(32), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("text_value", sa.Text()),
            sa.Column("bool_value", sa.Boolean()),
        )
    with Session(bind=connection) as session:
        for model, node_table in (
            (ArtifactRecord, "artifact_data_nodes"),
            (JobRecord, "job_data_nodes"),
        ):
            for record in session.scalars(sa.select(model)).all():
                values = {"metadata": record.parsed_metadata_snapshot}
                if model is JobRecord:
                    # Revision 0005 restores priority separately during its downgrade.
                    values.update(execution=record.execution_data, scheduling={})
                for field, value in values.items():
                    for node in encode(value, field):
                        connection.execute(
                            sa.text(
                                f"INSERT INTO {node_table} (owner_id, field, path, kind, text_value, bool_value) VALUES (:owner_id, :field, :path, :kind, :text_value, :bool_value)"
                            ),
                            {
                                "owner_id": record.id,
                                "text_value": None,
                                "bool_value": None,
                                **node,
                            },
                        )
    for name in JOB_COLUMNS:
        op.drop_column("jobs", name)
    for table in ("artifacts", "jobs"):
        for name in SNAPSHOT_COLUMNS:
            op.drop_column(table, name)
