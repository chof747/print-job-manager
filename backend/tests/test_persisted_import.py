import importlib
from pathlib import Path
from typing import Any, cast

import pytest

from backend.app.api.v1 import jobs


def test_uploaded_gcode_remains_available_from_artifact_storage_after_service_restart() -> (
    None
):
    repository = jobs.InMemoryImportRepository()
    content = b"G28\n"
    first_service = jobs.ImportService(repository=repository)
    imported = cast(
        dict[str, Any],
        first_service.import_gcode(
            filename="calibration-cube.gcode",
            media_type="text/x.gcode",
            content=content,
        ),
    )

    # Reloading the module models a new backend process with no module-global storage.
    importlib.reload(jobs)
    restarted_service = jobs.ImportService(repository=repository)

    assert isinstance(restarted_service.storage, jobs.FileSystemStorage)
    assert restarted_service.storage.retrieve(imported["artifact"]["id"]) == content


def test_fresh_import_service_loads_persisted_artifact_metadata_and_parser_snapshot() -> (
    None
):
    class PersistentImportRepository:
        def __init__(self) -> None:
            self.records: dict[str, dict[str, object]] = {}

        def save_import(
            self,
            *,
            artifact_id: str,
            filename: str,
            media_type: str,
            parsed: dict[str, object],
        ) -> None:
            self.records[artifact_id] = {
                "filename": filename,
                "mediaType": media_type,
                "parsed": parsed,
            }

        @property
        def imported_artifact_ids(self) -> set[str]:
            return set(self.records)

        def load_import(self, artifact_id: str) -> dict[str, object] | None:
            return self.records.get(artifact_id)

    class Parser:
        def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
            return {
                "extractedMetadata": {"material": "PLA", "estimatedDuration": 3600},
                "missingPlanningValues": [],
                "diagnostics": [],
            }

    repository = PersistentImportRepository()
    storage = jobs.InMemoryStorage()
    first_service = jobs.ImportService(
        storage=storage,
        parser=Parser(),
        repository=repository,
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = cast(
        dict[str, Any],
        first_service.import_gcode(
            filename="calibration-cube.gcode",
            media_type="text/x.gcode",
            content=b"G28\n",
        ),
    )

    restarted_service = jobs.ImportService(
        storage=storage,
        repository=repository,
        job_repository=jobs.InMemoryJobRepository(),
    )
    job = cast(
        dict[str, Any],
        restarted_service.create_job(
            artifact_id=imported["artifact"]["id"], material=None
        ),
    )

    assert job["executionData"] == {
        "artifactRef": imported["artifact"]["id"],
        "material": "PLA",
        "extractedMetadata": {"material": "PLA", "estimatedDuration": 3600},
    }


def test_failed_authoritative_import_does_not_leave_an_orphaned_artifact_file(
    tmp_path: Path,
) -> None:
    class FailingImportRepository:
        @property
        def imported_artifact_ids(self) -> set[str]:
            return set()

        def save_import(
            self,
            *,
            artifact_id: str,
            filename: str,
            media_type: str,
            parsed: dict[str, object],
        ) -> None:
            del artifact_id, filename, media_type, parsed
            raise RuntimeError("database unavailable")

        def load_import(self, artifact_id: str) -> dict[str, object] | None:
            del artifact_id
            return None

    storage_path = tmp_path / "artifacts"
    service = jobs.ImportService(
        storage=jobs.FileSystemStorage(storage_path),
        repository=FailingImportRepository(),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.import_gcode(
            filename="calibration-cube.gcode",
            media_type="text/x.gcode",
            content=b"G28\n",
        )

    assert not storage_path.exists() or list(storage_path.iterdir()) == []


def test_parser_failure_does_not_leave_a_newly_written_authoritative_artifact(
    tmp_path: Path,
) -> None:
    class FailingParser:
        def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
            del artifact_id, content
            raise RuntimeError("parser unavailable")

    storage_path = tmp_path / "artifacts"
    service = jobs.ImportService(
        storage=jobs.FileSystemStorage(storage_path),
        parser=FailingParser(),
        repository=jobs.InMemoryImportRepository(),
    )

    with pytest.raises(RuntimeError, match="parser unavailable"):
        service.import_gcode(
            filename="calibration-cube.gcode",
            media_type="text/x.gcode",
            content=b"G28\n",
        )

    assert not storage_path.exists() or list(storage_path.iterdir()) == []


def test_invalid_parser_output_does_not_leave_a_newly_written_artifact(
    tmp_path: Path,
) -> None:
    class InvalidOutputParser:
        def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
            del artifact_id, content
            return {
                "extractedMetadata": {},
                "missingPlanningValues": "material",
                "diagnostics": [],
            }

    storage_path = tmp_path / "artifacts"
    service = jobs.ImportService(
        storage=jobs.FileSystemStorage(storage_path),
        parser=InvalidOutputParser(),
        repository=jobs.InMemoryImportRepository(),
    )

    with pytest.raises(
        TypeError, match="parsed missingPlanningValues must be a list of strings"
    ):
        service.import_gcode(
            filename="calibration-cube.gcode",
            media_type="text/x.gcode",
            content=b"G28\n",
        )

    assert not storage_path.exists() or list(storage_path.iterdir()) == []
