import importlib

import pytest
from fastapi.testclient import TestClient


def test_registered_nozzle_and_build_volume_survive_reload_for_eligibility(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self: object, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {
                "material": "PLA",
                "nozzleDiameter": 0.4,
                "dimensions": {"x": 200.0, "y": 150.0, "z": 100.0},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    printer = client.put(
        "/api/v1/printers/printer-1",
        json={
            "enclosure": True,
            "nozzleDiameter": 0.4,
            "buildVolume": {"x": 200, "y": 200, "z": 200},
        },
    )
    assert printer.status_code in (200, 201)
    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 100},
    ).status_code == 201
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"requirements": {"material": {"color": "black", "amountGrams": 100}}},
    )
    assert created.status_code == 201

    from backend.app import main
    from backend.app.api import v1

    importlib.reload(jobs)
    importlib.reload(v1)
    importlib.reload(main)
    with TestClient(main.app) as fresh_client:
        result = fresh_client.post(
            f"/api/v1/jobs/{created.json()['id']}/eligibility",
            json={"printer": {"id": "printer-1"}},
        )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["failures"] == []
