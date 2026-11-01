from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from . import database
from .extraction_projection import extraction_facts
from .models import (
    ArtifactDiagnostic,
    ArtifactExtraction,
    ArtifactImport,
    ArtifactMissingPlanningValue,
    ArtifactRecord,
    ExtractionProvenance,
)


class SqlAlchemyImportRepository:
    def __init__(self, parser_id: str = "gcode-metadata", parser_version: str = "1") -> None:
        self.parser_id = parser_id
        self.parser_version = parser_version

    @property
    def imported_artifact_ids(self) -> set[str]:
        with database.SessionFactory() as session:
            return set(session.scalars(select(ArtifactRecord.id)))

    def save_import(
        self,
        *,
        artifact_id: str,
        filename: str,
        media_type: str,
        parsed: dict[str, object],
    ) -> str:
        with database.SessionFactory.begin() as session:
            artifact = ArtifactRecord(
                id=artifact_id,
                sha256=artifact_id.removeprefix("sha256:"),
                storage_key=artifact_id,
                filename=filename,
                media_type=media_type,
                parsed_metadata_snapshot=deepcopy(parsed),
            )
            values = {
                column.key: getattr(artifact, column.key)
                for column in ArtifactRecord.__table__.columns
                if getattr(artifact, column.key) is not None
            }
            session.execute(
                insert(ArtifactRecord)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["id"])
                .returning(ArtifactRecord.id)
            ).scalar_one_or_none()
            if True:
                extraction_id = str(uuid4())
                import_id = str(uuid4())
                session.add(
                    ArtifactExtraction(
                        id=extraction_id,
                        artifact_id=artifact_id,
                        parser=self.parser_id,
                        parser_version=self.parser_version,
                        has_extracted=artifact.snapshot_has_extracted,
                        has_provenance=artifact.snapshot_has_provenance,
                        material=artifact.snapshot_material,
                        filament_weight_grams=artifact.snapshot_weight,
                        estimated_duration=artifact.snapshot_duration,
                        nozzle_diameter=artifact.snapshot_nozzle_diameter,
                        layer_height=artifact.snapshot_layer_height,
                        dimension_x=artifact.snapshot_dimension_x,
                        dimension_y=artifact.snapshot_dimension_y,
                        dimension_z=artifact.snapshot_dimension_z,
                        slicer=artifact.snapshot_slicer,
                        printer_profile=artifact.snapshot_printer_profile,
                    )
                )
                session.flush()
                session.add(ArtifactImport(
                    id=import_id, artifact_id=artifact_id, extraction_id=extraction_id,
                    filename=filename, media_type=media_type,
                ))
                for field, parser, source in (
                    ("material", artifact.material_parser, artifact.material_source),
                    ("estimatedDuration", artifact.duration_parser, artifact.duration_source),
                    ("filamentWeightGrams", artifact.weight_parser, artifact.weight_source),
                    ("nozzleDiameter", artifact.nozzle_parser, artifact.nozzle_source),
                    ("layerHeight", artifact.layer_parser, artifact.layer_source),
                    ("dimensions", artifact.dimensions_parser, artifact.dimensions_source),
                    ("slicer", artifact.slicer_parser, artifact.slicer_source),
                    ("printerProfile", artifact.printer_profile_parser, artifact.printer_profile_source),
                ):
                    if parser is not None:
                        session.add(
                            ExtractionProvenance(
                                extraction_id=extraction_id,
                                field=field,
                                parser=parser,
                                source_key=source,
                            )
                        )
                session.add_all(
                    ArtifactMissingPlanningValue(
                        artifact_id=artifact_id,
                        extraction_id=extraction_id,
                        position=record.position,
                        planning_value=record.planning_value,
                    )
                    for record in artifact.missing_value_records
                )
                session.add_all(
                    ArtifactDiagnostic(
                        artifact_id=artifact_id,
                        extraction_id=extraction_id,
                        position=record.position,
                        code=record.code,
                        source_key=record.source_key,
                    )
                    for record in artifact.diagnostic_records
                )
            return import_id

    def load_import(self, artifact_id: str) -> dict[str, object] | None:
        with database.SessionFactory() as session:
            context = session.get(ArtifactImport, artifact_id)
            if context is None:
                context = session.scalar(
                    select(ArtifactImport).where(ArtifactImport.artifact_id == artifact_id)
                    .order_by(ArtifactImport.position).limit(1)
                )
            if context is None:
                return None
            artifact_id = context.artifact_id
            artifact = session.get(ArtifactRecord, artifact_id)
            if artifact is None:
                return None
            extraction = session.get(ArtifactExtraction, context.extraction_id)
            if extraction is None:
                raise RuntimeError("artifact extraction does not exist")
            parsed = extraction_facts(session, artifact, extraction)
            return {
                "filename": context.filename,
                "mediaType": context.media_type,
                "artifact_id": artifact_id,
                "parsed": parsed,
                "extraction": {
                    "id": extraction.id,
                    "parser": extraction.parser,
                    "parserVersion": extraction.parser_version,
                },
            }

    def load_context(self, identifier: str) -> dict[str, str] | None:
        with database.SessionFactory() as session:
            context = session.get(ArtifactImport, identifier)
            if context is None:
                context = session.scalar(
                    select(ArtifactImport).where(ArtifactImport.artifact_id == identifier)
                    .order_by(ArtifactImport.position).limit(1)
                )
            if context is None:
                return None
            return {"id": context.id, "artifact_id": context.artifact_id,
                    "filename": context.filename, "mediaType": context.media_type}
