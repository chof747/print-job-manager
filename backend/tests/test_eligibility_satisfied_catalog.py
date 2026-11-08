import pytest
from fastapi.testclient import TestClient


def test_eligibility_explains_all_applicable_satisfied_requirements(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    def parse(self: object, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {
                "material": "PLA",
                "nozzleDiameter": 0.4,
                "dimensions": {"x": 100, "y": 100, "z": 100},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    printer = client.put(
        "/api/v1/printers/printer-1",
        json={
            "enclosure": True,
            "hardenedNozzle": True,
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
        json={"requirements": {
            "enclosure": True,
            "hardenedNozzle": True,
            "material": {"color": "black", "amountGrams": 100},
        }},
    )
    assert created.status_code == 201
    job = created.json()
    updated = client.patch(
        f"/api/v1/jobs/{job['id']}/scheduling",
        json={"expectedVersion": job["version"], "printerAssignment": {"mode": "required", "printerId": "printer-1"}},
    )
    assert updated.status_code == 200

    result = client.post(
        f"/api/v1/jobs/{job['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    codes = {item["code"] for item in result.json()["satisfied"]}
    assert {
        "enclosure_satisfied",
        "hardened_nozzle_satisfied",
        "nozzle_diameter_satisfied",
        "build_volume_satisfied",
        "material_satisfied",
        "required_printer_satisfied",
    } <= codes
