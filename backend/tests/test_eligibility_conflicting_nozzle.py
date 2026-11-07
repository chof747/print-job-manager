import pytest
from fastapi.testclient import TestClient


def test_extracted_nozzle_remains_authoritative_for_eligibility(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self: object, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "nozzleDiameter": 0.4},
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201

    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"nozzleDiameter": 0.6},
    )

    assert created.status_code == 201
    assert created.json()["executionData"]["nozzleDiameter"] == 0.4
    assert client.put(
        "/api/v1/printers/printer-1", json={"enclosure": True, "nozzleDiameter": 0.6}
    ).status_code in (200, 201)
    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 100},
    ).status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "nozzle_diameter_mismatch" in [
        failure["code"] for failure in result.json()["failures"]
    ]
