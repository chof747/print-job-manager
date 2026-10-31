import pytest
from fastapi.testclient import TestClient


def test_identical_uploads_create_jobs_from_their_own_extraction(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    materials = iter(("PLA", "PETG"))

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        material = next(materials)
        return {
            "extractedMetadata": {"material": material},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"}
            },
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
    assert first.json()["artifact"]["id"] == second.json()["artifact"]["id"]
    first_id = first.json()["import"]["id"]
    second_id = second.json()["import"]["id"]

    jobs.import_service = jobs.ImportService()
    first_job = client.post(f"/api/v1/import/{first_id}/jobs", json={})
    second_job = client.post(f"/api/v1/import/{second_id}/jobs", json={})
    assert first_job.status_code == second_job.status_code == 201
    assert first_job.json()["executionData"]["material"] == "PLA"
    assert second_job.json()["executionData"]["material"] == "PETG"

    jobs.import_service = jobs.ImportService()
    first_detail = client.get(f"/api/v1/jobs/{first_job.json()['id']}")
    assert first_detail.status_code == 200
    assert first_detail.json()["executionData"]["material"] == "PLA"
