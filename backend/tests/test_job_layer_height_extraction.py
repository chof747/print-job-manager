import pytest
from fastapi.testclient import TestClient


def test_job_creation_preserves_persisted_layer_height(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "layerHeight": 0.2},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"},
                "layerHeight": {"parser": "prusa-family", "sourceKey": "layer_height"},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]
    jobs.import_service = jobs.ImportService()
    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        created = error_client.post(f"/api/v1/import/{artifact_id}/jobs", json={})
    assert created.status_code == 201

    jobs.import_service = jobs.ImportService()
    detail = client.get(f"/api/v1/jobs/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["executionData"]["extractedMetadata"]["layerHeight"] == 0.2
