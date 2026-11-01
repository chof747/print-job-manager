import pytest
from fastapi.testclient import TestClient


def test_parser_nozzle_diameter_survives_persisted_import_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "nozzleDiameter": 0.4},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"},
                "nozzleDiameter": {"parser": "prusa-family", "sourceKey": "nozzle_diameter"},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        response = error_client.post(
            "/api/v1/import",
            files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
        )
    assert response.status_code == 201
    artifact_id = response.json()["artifact"]["id"]

    jobs.import_service = jobs.ImportService()
    review = client.get(f"/api/v1/import/{artifact_id}")
    assert review.status_code == 200
    assert review.json()["extractedMetadata"]["nozzleDiameter"] == 0.4
    assert review.json()["provenance"]["nozzleDiameter"]["sourceKey"] == "nozzle_diameter"
