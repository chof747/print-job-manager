import re
from copy import deepcopy
from threading import Lock

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict


router = APIRouter()


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    material: str | None = None


class InMemoryStorage:
    def __init__(self) -> None:
        self.artifact_ids: set[str] = set()
        self.artifacts: dict[str, bytes] = {}

    def store(self, *, filename: str, media_type: str, content: bytes) -> str:
        artifact_name = re.sub(
            r"[^a-z0-9]+", "-", filename.rsplit(".", 1)[0].lower()
        ).strip("-")
        artifact_id = f"artifact-{artifact_name}"
        suffix = 2
        while artifact_id in self.artifact_ids:
            artifact_id = f"artifact-{artifact_name}-{suffix}"
            suffix += 1
        self.artifact_ids.add(artifact_id)
        self.artifacts[artifact_id] = content
        return artifact_id

    def retrieve(self, artifact_id: str) -> bytes:
        return self.artifacts[artifact_id]


class GcodeParser:
    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {"missingPlanningValues": ["material"], "diagnostics": []}


class InMemoryImportRepository:
    def __init__(self) -> None:
        self.imported_artifact_ids: set[str] = set()

    def save_import(
        self,
        *,
        artifact_id: str,
        filename: str,
        media_type: str,
        parsed: dict[str, object],
    ) -> None:
        self.imported_artifact_ids.add(artifact_id)


class ImportService:
    def __init__(
        self,
        storage: object | None = None,
        parser: object | None = None,
        repository: object | None = None,
    ) -> None:
        self.active_jobs: list[dict[str, object]] = []
        self.active_jobs_lock = Lock()
        self.import_missing_planning_values: dict[str, list[object]] = {}
        self.import_extracted_metadata: dict[str, object] = {}
        self.storage = storage or InMemoryStorage()
        self.parser = parser or GcodeParser()
        self.repository = repository or InMemoryImportRepository()

    def import_gcode(
        self, *, filename: str, media_type: str, content: bytes
    ) -> dict[str, object]:
        artifact_id = self.storage.store(
            filename=filename, media_type=media_type, content=content
        )
        parsed = self.parser.parse(artifact_id=artifact_id, content=content)
        self.repository.save_import(
            artifact_id=artifact_id,
            filename=filename,
            media_type=media_type,
            parsed=parsed,
        )
        self.import_missing_planning_values[artifact_id] = parsed["missingPlanningValues"]
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
            "missingPlanningValues": parsed["missingPlanningValues"],
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
        if artifact_id not in self.repository.imported_artifact_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if artifact_id in self.import_extracted_metadata:
            extracted_metadata = self.import_extracted_metadata[artifact_id]
            if isinstance(extracted_metadata, dict):
                extracted_material = extracted_metadata.get("material")
                if isinstance(extracted_material, str):
                    material = extracted_material
        planning_values = planning_values or {}
        planning_values["material"] = material
        missing_values = [
            value
            for value in self.import_missing_planning_values[artifact_id]
            if value not in planning_values
            or planning_values[value] is None
            or (
                isinstance(planning_values[value], str)
                and not planning_values[value].strip()
            )
        ]
        if missing_values:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"missingPlanningValues": missing_values},
            )

        execution_data = {
            "artifactRef": artifact_id,
            "material": material,
        }
        execution_data.update(
            {
                value: deepcopy(planning_values[value])
                for value in self.import_missing_planning_values[artifact_id]
            }
        )
        if artifact_id in self.import_extracted_metadata:
            execution_data["extractedMetadata"] = deepcopy(
                self.import_extracted_metadata[artifact_id]
            )

        job = {
            "id": f"job-{artifact_id}",
            "state": "ready",
            "executionData": execution_data,
            "schedulingData": {"priority": 0},
        }
        with self.active_jobs_lock:
            for existing_job in self.active_jobs:
                if existing_job["executionData"]["artifactRef"] == artifact_id:
                    return existing_job, False
            self.active_jobs.append(job)
        return job, True

    def active_queue(self) -> dict[str, list[object]]:
        return {"jobs": self.active_jobs}


import_service = ImportService()


def get_import_service() -> ImportService:
    return import_service


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_gcode(file: UploadFile = File(...)) -> dict[str, object]:
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
