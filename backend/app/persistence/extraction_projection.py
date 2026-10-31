"""Reconstruct the public extraction facts from typed persistence records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    ArtifactDiagnostic,
    ArtifactExtraction,
    ArtifactMissingPlanningValue,
    ArtifactRecord,
    ExtractionProvenance,
)


def extraction_facts(session: Session, artifact: ArtifactRecord, extraction: ArtifactExtraction) -> dict:
    parsed: dict = {}
    missing = session.scalars(
        select(ArtifactMissingPlanningValue)
        .where(ArtifactMissingPlanningValue.extraction_id == extraction.id)
        .order_by(ArtifactMissingPlanningValue.position)
    )
    parsed["missingPlanningValues"] = [item.planning_value for item in missing]
    diagnostics = session.scalars(
        select(ArtifactDiagnostic)
        .where(ArtifactDiagnostic.extraction_id == extraction.id)
        .order_by(ArtifactDiagnostic.position)
    )
    parsed["diagnostics"] = [
        {"code": item.code, "sourceKey": item.source_key} for item in diagnostics
    ]
    if extraction.has_extracted:
        metadata = {
            key: value for key, value in (
                ("material", extraction.material),
                ("estimatedDuration", extraction.estimated_duration),
                ("filamentWeightGrams", extraction.filament_weight_grams),
                ("nozzleDiameter", extraction.nozzle_diameter),
                ("layerHeight", extraction.layer_height),
                ("slicer", extraction.slicer),
                ("printerProfile", extraction.printer_profile),
            ) if value is not None
        }
        if extraction.dimension_x is not None:
            metadata["dimensions"] = {
                "x": extraction.dimension_x, "y": extraction.dimension_y,
                "z": extraction.dimension_z,
            }
        parsed["extractedMetadata"] = metadata
    if extraction.has_provenance:
        provenance = session.scalars(
            select(ExtractionProvenance).where(ExtractionProvenance.extraction_id == extraction.id)
        )
        parsed["provenance"] = {
            item.field: {"parser": item.parser, "sourceKey": item.source_key}
            for item in provenance
        }
    return parsed
