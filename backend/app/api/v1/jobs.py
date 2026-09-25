import hashlib
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Protocol

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from ...config import get_settings
from ...persistence.database import SessionFactory
from ...persistence.job_repository import SqlAlchemyJobRepository
from ...persistence.models import ArtifactRecord

router = APIRouter()


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    material: str | None = None


class ArtifactStorage(Protocol):
    def store(self, *, filename: str, media_type: str, content: bytes) -> str: ...


class GcodeParsingService(Protocol):
    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]: ...


class ImportRepository(Protocol):
    @property
    def imported_artifact_ids(self) -> set[str]: ...

    def save_import(
        self,
        *,
        artifact_id: str,
        filename: str,
        media_type: str,
        parsed: dict[str, object],
    ) -> None: ...

    def load_import(self, artifact_id: str) -> dict[str, object] | None: ...


class JobRepository(Protocol):
    def create_ready_job(
        self, *, job: dict[str, object], creation_history: dict[str, object]
    ) -> tuple[dict[str, object], bool]: ...

    def active_queue(self) -> dict[str, list[object]]: ...

    def get_job(self, job_id: str) -> dict[str, object] | None: ...


class InMemoryStorage:
    def __init__(self) -> None:
        self.artifact_ids: set[str] = set()
        self.artifacts: dict[str, bytes] = {}

    def store(self, *, filename: str, media_type: str, content: bytes) -> str:
        artifact_id = f"sha256:{hashlib.sha256(content).hexdigest()}"
        self.artifact_ids.add(artifact_id)
        self.artifacts[artifact_id] = content
        return artifact_id

    def retrieve(self, artifact_id: str) -> bytes:
        return self.artifacts[artifact_id]


class FileSystemStorage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def store(self, *, filename: str, media_type: str, content: bytes) -> str:
        del filename, media_type
        artifact_id = f"sha256:{hashlib.sha256(content).hexdigest()}"
        self.path.mkdir(parents=True, exist_ok=True)
        target = self.path / artifact_id.removeprefix("sha256:")
        descriptor, temporary_path = tempfile.mkstemp(dir=self.path)
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, target)
            directory_descriptor = os.open(self.path, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return artifact_id

    def retrieve(self, artifact_id: str) -> bytes:
        content = (self.path / artifact_id.removeprefix("sha256:")).read_bytes()
        if f"sha256:{hashlib.sha256(content).hexdigest()}" != artifact_id:
            raise ValueError("artifact content does not match its sha256 identifier")
        return content

    def delete(self, artifact_id: str) -> None:
        (self.path / artifact_id.removeprefix("sha256:")).unlink(missing_ok=True)


artifact_storage = FileSystemStorage(get_settings().artifact_storage_path)


class GcodeParser:
    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {"missingPlanningValues": ["material"], "diagnostics": []}


class InMemoryImportRepository:
    def __init__(self) -> None:
        self.imported_artifact_ids: set[str] = set()
        self.records: dict[str, dict[str, object]] = {}

    def save_import(
        self,
        *,
        artifact_id: str,
        filename: str,
        media_type: str,
        parsed: dict[str, object],
    ) -> None:
        self.imported_artifact_ids.add(artifact_id)
        self.records[artifact_id] = {
            "filename": filename,
            "mediaType": media_type,
            "parsed": deepcopy(parsed),
        }

    def load_import(self, artifact_id: str) -> dict[str, object] | None:
        record = self.records.get(artifact_id)
        return deepcopy(record) if record is not None else None


class SqlAlchemyImportRepository:
    @property
    def imported_artifact_ids(self) -> set[str]:
        with SessionFactory() as session:
            return set(session.scalars(select(ArtifactRecord.id)))

    def save_import(
        self,
        *,
        artifact_id: str,
        filename: str,
        media_type: str,
        parsed: dict[str, object],
    ) -> None:
        del filename, media_type
        with SessionFactory.begin() as session:
            session.merge(
                ArtifactRecord(
                    id=artifact_id,
                    sha256=artifact_id.removeprefix("sha256:"),
                    storage_key=artifact_id,
                    parsed_metadata_snapshot=deepcopy(parsed),
                )
            )

    def load_import(self, artifact_id: str) -> dict[str, object] | None:
        with SessionFactory() as session:
            artifact = session.get(ArtifactRecord, artifact_id)
            if artifact is None:
                return None
            return {"parsed": deepcopy(artifact.parsed_metadata_snapshot)}


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.active_jobs: list[dict[str, object]] = []
        self.job_history: list[dict[str, object]] = []
        self.lock = Lock()

    def create_ready_job(
        self, *, job: dict[str, object], creation_history: dict[str, object]
    ) -> tuple[dict[str, object], bool]:
        with self.lock:
            for existing_job in self.active_jobs:
                existing_execution_data = existing_job.get("executionData")
                execution_data = job.get("executionData")
                if (
                    isinstance(existing_execution_data, dict)
                    and isinstance(execution_data, dict)
                    and existing_execution_data.get("artifactRef")
                    == execution_data.get("artifactRef")
                ):
                    return existing_job, False
            self.active_jobs.append(job)
            self.job_history.append(creation_history)
        return job, True

    def active_queue(self) -> dict[str, list[object]]:
        with self.lock:
            jobs: list[object] = []
            for job in self.active_jobs:
                jobs.append(deepcopy(job))
            return {"jobs": jobs}

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with self.lock:
            for job in self.active_jobs:
                if job["id"] == job_id:
                    return deepcopy(job)
        return None


class ImportService:
    def __init__(
        self,
        storage: ArtifactStorage | None = None,
        parser: GcodeParsingService | None = None,
        repository: ImportRepository | None = None,
        job_repository: JobRepository | None = None,
    ) -> None:
        self.import_missing_planning_values: dict[str, list[str]] = {}
        self.import_extracted_metadata: dict[str, object] = {}
        self.storage = storage or artifact_storage
        self.parser = parser or GcodeParser()
        self.repository = repository or (
            InMemoryImportRepository()
            if storage is not None or parser is not None
            else SqlAlchemyImportRepository()
        )
        # Unit callers can supply an isolated import boundary without requiring a DB.
        self.job_repository = job_repository or (
            InMemoryJobRepository()
            if storage is not None or parser is not None or repository is not None
            else SqlAlchemyJobRepository()
        )

    def import_gcode(
        self, *, filename: str, media_type: str, content: bytes
    ) -> dict[str, object]:
        artifact_id = f"sha256:{hashlib.sha256(content).hexdigest()}"
        artifact_existed = (
            isinstance(self.storage, FileSystemStorage)
            and (self.storage.path / artifact_id.removeprefix("sha256:")).exists()
        )
        artifact_id = self.storage.store(
            filename=filename, media_type=media_type, content=content
        )
        try:
            parsed = self.parser.parse(artifact_id=artifact_id, content=content)
            missing_planning_values = _missing_planning_values(parsed)
            self.repository.save_import(
                artifact_id=artifact_id,
                filename=filename,
                media_type=media_type,
                parsed=parsed,
            )
        except Exception:
            if isinstance(self.storage, FileSystemStorage) and not artifact_existed:
                self.storage.delete(artifact_id)
            raise
        self.import_missing_planning_values[artifact_id] = missing_planning_values
        if "extractedMetadata" in parsed:
            self.import_extracted_metadata[artifact_id] = deepcopy(
                parsed["extractedMetadata"]
            )

        return {
            "artifact": {
                "id": artifact_id,
                "filename": filename,
                "mediaType": media_type,
            },
            "missingPlanningValues": missing_planning_values,
            "diagnostics": parsed["diagnostics"],
        }

    def create_job(
        self,
        *,
        artifact_id: str,
        material: str | None,
        planning_values: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.create_job_with_status(
            artifact_id=artifact_id,
            material=material,
            planning_values=planning_values,
        )[0]

    def create_job_with_status(
        self,
        *,
        artifact_id: str,
        material: str | None,
        planning_values: dict[str, object] | None = None,
    ) -> tuple[dict[str, object], bool]:
        record_loader = getattr(self.repository, "load_import", None)
        record = record_loader(artifact_id) if callable(record_loader) else None
        if record is not None:
            parsed = record["parsed"]
            if not isinstance(parsed, dict):
                raise TypeError("persisted import parsed snapshot must be an object")
            missing_planning_values = _missing_planning_values(parsed)
            extracted_metadata = parsed.get("extractedMetadata")
        elif artifact_id in self.repository.imported_artifact_ids:
            missing_planning_values = self.import_missing_planning_values[artifact_id]
            extracted_metadata = self.import_extracted_metadata.get(artifact_id)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if isinstance(extracted_metadata, dict):
            extracted_material = extracted_metadata.get("material")
            if isinstance(extracted_material, str):
                material = extracted_material
        planning_values = planning_values or {}
        planning_values["material"] = material
        missing_values = []
        for value in missing_planning_values:
            planning_value = planning_values.get(value)
            if planning_value is None or (
                isinstance(planning_value, str) and not planning_value.strip()
            ):
                missing_values.append(value)
        if missing_values:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"missingPlanningValues": missing_values},
            )

        execution_data: dict[str, object] = {
            "artifactRef": artifact_id,
            "material": material,
        }
        execution_data.update(
            {
                value: deepcopy(planning_values[value])
                for value in missing_planning_values
            }
        )
        if extracted_metadata is not None:
            execution_data["extractedMetadata"] = deepcopy(extracted_metadata)

        job: dict[str, object] = {
            "id": f"job-{artifact_id}",
            "state": "ready",
            "executionData": execution_data,
            "schedulingData": {"priority": 0},
        }
        return self.job_repository.create_ready_job(
            job=job,
            creation_history={"jobId": job["id"], "state": "ready"},
        )

    def active_queue(self) -> dict[str, list[object]]:
        return self.job_repository.active_queue()

    def get_job(self, job_id: str) -> dict[str, object] | None:
        return self.job_repository.get_job(job_id)


def _missing_planning_values(parsed: dict[str, object]) -> list[str]:
    missing_planning_values = parsed.get("missingPlanningValues")
    if not isinstance(missing_planning_values, list) or not all(
        isinstance(value, str) for value in missing_planning_values
    ):
        raise TypeError("parsed missingPlanningValues must be a list of strings")
    return missing_planning_values


import_service = ImportService()


def get_import_service() -> ImportService:
    return import_service


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_gcode(file: UploadFile = File(...)) -> dict[str, object]:  # noqa: B008
    filename = file.filename or "upload"
    if not filename.lower().endswith(".gcode"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    return get_import_service().import_gcode(
        filename=filename,
        media_type=file.content_type or "application/octet-stream",
        content=await file.read(),
    )


@router.post("/import/{artifact_id}/jobs", status_code=status.HTTP_201_CREATED)
async def create_job_from_import(
    artifact_id: str, request: CreateJobRequest, response: Response
) -> dict[str, object]:
    planning_values = request.model_dump()
    job, created = get_import_service().create_job_with_status(
        artifact_id=artifact_id,
        material=request.material,
        planning_values=planning_values,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return job


@router.get("/queue")
def queue() -> dict[str, list[object]]:
    return get_import_service().active_queue()


@router.get("/jobs/{job_id}")
def job_detail(job_id: str) -> dict[str, object]:
    job = get_import_service().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return job
