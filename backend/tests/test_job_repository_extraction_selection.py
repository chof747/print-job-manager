import pytest
from fastapi.testclient import TestClient


def test_repository_uses_selected_extraction_for_job_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence.job_repository import SqlAlchemyJobRepository

    materials = iter(("PLA", "PETG"))

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": next(materials)},
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    first = client.post(
        "/api/v1/import", files={"file": ("first.gcode", b"G28\n", "text/x.gcode")}
    )
    second = client.post(
        "/api/v1/import", files={"file": ("second.gcode", b"G28\n", "text/x.gcode")}
    )
    assert first.status_code == second.status_code == 201
    artifact_id = first.json()["artifact"]["id"]
    assert second.json()["artifact"]["id"] == artifact_id
    persisted = jobs.SqlAlchemyImportRepository().load_import(second.json()["import"]["id"])
    assert persisted is not None

    repository = SqlAlchemyJobRepository()
    created, was_created = repository.create_ready_job(
        job={
            "id": "selected-extraction-job",
            "state": "ready",
            "executionData": {"artifactRef": artifact_id, "material": "PETG"},
            "schedulingData": {"priority": 0},
            "_extraction_id": persisted["extraction"]["id"],
        },
        creation_history={"jobId": "selected-extraction-job", "state": "ready"},
    )
    assert was_created
    assert created["parsedMetadataSnapshot"]["extractedMetadata"]["material"] == "PETG"
    assert repository.get_job("selected-extraction-job") == created
