import pytest
from fastapi.testclient import TestClient


def test_unsupported_parser_field_is_not_retained_or_blocking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "futureField": "not-retained"},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"},
                "futureField": {"parser": "prusa-family", "sourceKey": "future_key"},
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
    assert review.json()["extractedMetadata"] == {"material": "PLA"}
    assert "futureField" not in review.json().get("provenance", {})
    created = client.post(f"/api/v1/import/{artifact_id}/jobs", json={})
    assert created.status_code == 201
    assert created.json()["executionData"]["material"] == "PLA"
