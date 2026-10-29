from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from .database import Base


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
        known = {
            "artifactRef",
            "material",
            "artifactFilename",
            "extractedMetadata",
            "nozzleDiameter",
        }
        if set(value) - known:
            raise ValueError(
                "Unsupported planning facts: " + ", ".join(sorted(set(value) - known))
            )
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
