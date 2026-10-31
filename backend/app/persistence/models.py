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
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    snapshot_nozzle_diameter: Mapped[float | None] = mapped_column(Float)
    snapshot_layer_height: Mapped[float | None] = mapped_column(Float)
    snapshot_dimension_x: Mapped[float | None] = mapped_column(Float)
    snapshot_dimension_y: Mapped[float | None] = mapped_column(Float)
    snapshot_dimension_z: Mapped[float | None] = mapped_column(Float)
    snapshot_slicer: Mapped[str | None] = mapped_column(Text)
    snapshot_printer_profile: Mapped[str | None] = mapped_column(Text)
    material_parser: Mapped[str | None] = mapped_column(Text)
    material_source: Mapped[str | None] = mapped_column(Text)
    duration_parser: Mapped[str | None] = mapped_column(Text)
    duration_source: Mapped[str | None] = mapped_column(Text)
    weight_parser: Mapped[str | None] = mapped_column(Text)
    weight_source: Mapped[str | None] = mapped_column(Text)
    nozzle_parser: Mapped[str | None] = mapped_column(Text)
    nozzle_source: Mapped[str | None] = mapped_column(Text)
    layer_parser: Mapped[str | None] = mapped_column(Text)
    layer_source: Mapped[str | None] = mapped_column(Text)
    dimensions_parser: Mapped[str | None] = mapped_column(Text)
    dimensions_source: Mapped[str | None] = mapped_column(Text)
    slicer_parser: Mapped[str | None] = mapped_column(Text)
    slicer_source: Mapped[str | None] = mapped_column(Text)
    printer_profile_parser: Mapped[str | None] = mapped_column(Text)
    printer_profile_source: Mapped[str | None] = mapped_column(Text)

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
                    ("nozzleDiameter", self.snapshot_nozzle_diameter),
                    ("layerHeight", self.snapshot_layer_height),
                    ("slicer", self.snapshot_slicer),
                    ("printerProfile", self.snapshot_printer_profile),
                )
                if value is not None
            }
            if self.snapshot_dimension_x is not None:
                result["extractedMetadata"]["dimensions"] = {
                    "x": self.snapshot_dimension_x,
                    "y": self.snapshot_dimension_y,
                    "z": self.snapshot_dimension_z,
                }
        if self.snapshot_has_provenance:
            result["provenance"] = {
                key: {"parser": parser, "sourceKey": source}
                for key, parser, source in (
                    ("material", self.material_parser, self.material_source),
                    ("estimatedDuration", self.duration_parser, self.duration_source),
                    ("filamentWeightGrams", self.weight_parser, self.weight_source),
                    ("nozzleDiameter", self.nozzle_parser, self.nozzle_source),
                    ("layerHeight", self.layer_parser, self.layer_source),
                    ("dimensions", self.dimensions_parser, self.dimensions_source),
                    ("slicer", self.slicer_parser, self.slicer_source),
                    ("printerProfile", self.printer_profile_parser, self.printer_profile_source),
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
        fields = {
            "material", "estimatedDuration", "filamentWeightGrams", "nozzleDiameter",
            "layerHeight", "dimensions", "slicer", "printerProfile",
        }
        _keys(extracted, fields)
        _keys(provenance, fields)
        self.snapshot_material = extracted.get("material")
        self.snapshot_duration = extracted.get("estimatedDuration")
        self.snapshot_weight = extracted.get("filamentWeightGrams")
        self.snapshot_nozzle_diameter = extracted.get("nozzleDiameter")
        self.snapshot_layer_height = extracted.get("layerHeight")
        self.snapshot_slicer = extracted.get("slicer")
        self.snapshot_printer_profile = extracted.get("printerProfile")
        dimensions = extracted.get("dimensions")
        if dimensions is not None:
            _keys(dimensions, {"x", "y", "z"}, required=True)
        self.snapshot_dimension_x = dimensions["x"] if dimensions is not None else None
        self.snapshot_dimension_y = dimensions["y"] if dimensions is not None else None
        self.snapshot_dimension_z = dimensions["z"] if dimensions is not None else None
        for key, prefix in (
            ("material", "material"),
            ("estimatedDuration", "duration"),
            ("filamentWeightGrams", "weight"),
            ("nozzleDiameter", "nozzle"),
            ("layerHeight", "layer"),
            ("dimensions", "dimensions"),
            ("slicer", "slicer"),
            ("printerProfile", "printer_profile"),
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
    missing_values: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    diagnostic_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    diagnostic_sources: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    artifact_ref: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id"), nullable=False
    )
    extraction_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("artifact_extractions.id")
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
    execution_nozzle_diameter: Mapped[float | None] = mapped_column(Float)
    execution_layer_height: Mapped[float | None] = mapped_column(Float)
    execution_dimension_x: Mapped[float | None] = mapped_column(Float)
    execution_dimension_y: Mapped[float | None] = mapped_column(Float)
    execution_dimension_z: Mapped[float | None] = mapped_column(Float)
    execution_slicer: Mapped[str | None] = mapped_column(Text)
    execution_printer_profile: Mapped[str | None] = mapped_column(Text)
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
                    ("nozzleDiameter", self.execution_nozzle_diameter),
                    ("layerHeight", self.execution_layer_height),
                    ("slicer", self.execution_slicer),
                    ("printerProfile", self.execution_printer_profile),
                )
                if value is not None
            }
            if self.execution_dimension_x is not None:
                result["extractedMetadata"]["dimensions"] = {
                    "x": self.execution_dimension_x,
                    "y": self.execution_dimension_y,
                    "z": self.execution_dimension_z,
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
        _keys(extracted, {"material", "estimatedDuration", "filamentWeightGrams", "nozzleDiameter", "layerHeight", "dimensions", "slicer", "printerProfile"})
        self.execution_material = extracted.get("material")
        self.execution_duration = extracted.get("estimatedDuration")
        self.execution_weight = extracted.get("filamentWeightGrams")
        self.execution_nozzle_diameter = extracted.get("nozzleDiameter")
        self.execution_layer_height = extracted.get("layerHeight")
        self.execution_slicer = extracted.get("slicer")
        self.execution_printer_profile = extracted.get("printerProfile")
        dimensions = extracted.get("dimensions")
        if dimensions is not None:
            _keys(dimensions, {"x", "y", "z"}, required=True)
        self.execution_dimension_x = dimensions["x"] if dimensions is not None else None
        self.execution_dimension_y = dimensions["y"] if dimensions is not None else None
        self.execution_dimension_z = dimensions["z"] if dimensions is not None else None

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
    media_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="application/octet-stream"
    )
    estimated_duration: Mapped[int | None] = mapped_column(NumericInteger())
    filament_weight_grams: Mapped[float | None] = mapped_column(Float)
    missing_value_records: Mapped[list["ArtifactMissingPlanningValue"]] = relationship(
        order_by="ArtifactMissingPlanningValue.position", cascade="all, delete-orphan"
    )
    diagnostic_records: Mapped[list["ArtifactDiagnostic"]] = relationship(
        order_by="ArtifactDiagnostic.position", cascade="all, delete-orphan"
    )

    @property
    def missing_values(self):
        return [record.planning_value for record in self.missing_value_records]

    @missing_values.setter
    def missing_values(self, values):
        self.missing_value_records = [
            ArtifactMissingPlanningValue(position=position, planning_value=value)
            for position, value in enumerate(values)
        ]

    @property
    def diagnostic_codes(self):
        return [record.code for record in self.diagnostic_records]

    @diagnostic_codes.setter
    def diagnostic_codes(self, values):
        self.diagnostic_records = [
            ArtifactDiagnostic(position=position, code=value, source_key="")
            for position, value in enumerate(values)
        ]

    @property
    def diagnostic_sources(self):
        return [record.source_key for record in self.diagnostic_records]

    @diagnostic_sources.setter
    def diagnostic_sources(self, values):
        for record, value in zip(self.diagnostic_records, values, strict=True):
            record.source_key = value

    @property
    def parsed_metadata_snapshot(self):
        return super().parsed_metadata_snapshot

    @parsed_metadata_snapshot.setter
    def parsed_metadata_snapshot(self, value):
        self._set_snapshot(value)
        self.estimated_duration = self.snapshot_duration
        self.filament_weight_grams = self.snapshot_weight


class ArtifactMissingPlanningValue(Base):
    __tablename__ = "artifact_missing_planning_values"
    artifact_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    extraction_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifact_extractions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    planning_value: Mapped[str] = mapped_column(Text, nullable=False)


class ArtifactDiagnostic(Base):
    __tablename__ = "artifact_diagnostics"
    artifact_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    extraction_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifact_extractions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str] = mapped_column(Text, nullable=False)


class ArtifactExtraction(Base):
    __tablename__ = "artifact_extractions"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    parser: Mapped[str] = mapped_column(Text, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False, server_default="unknown")
    has_extracted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_provenance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    material: Mapped[str | None] = mapped_column(Text)
    filament_weight_grams: Mapped[float | None] = mapped_column(Float)
    estimated_duration: Mapped[int | None] = mapped_column(NumericInteger())
    nozzle_diameter: Mapped[float | None] = mapped_column(Float)
    layer_height: Mapped[float | None] = mapped_column(Float)
    dimension_x: Mapped[float | None] = mapped_column(Float)
    dimension_y: Mapped[float | None] = mapped_column(Float)
    dimension_z: Mapped[float | None] = mapped_column(Float)
    slicer: Mapped[str | None] = mapped_column(Text)
    printer_profile: Mapped[str | None] = mapped_column(Text)


class ArtifactImport(Base):
    __tablename__ = "artifact_imports"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    extraction_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifact_extractions.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)


class ExtractionProvenance(Base):
    __tablename__ = "extraction_provenance"
    __table_args__ = (
        CheckConstraint(
            "field IN ('material', 'estimatedDuration', 'filamentWeightGrams', 'nozzleDiameter', 'layerHeight', 'dimensions', 'slicer', 'printerProfile')",
            name="ck_extraction_provenance_field",
        ),
    )
    extraction_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("artifact_extractions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    field: Mapped[str] = mapped_column(Text, primary_key=True)
    parser: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str] = mapped_column(Text, nullable=False)
