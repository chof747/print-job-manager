import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs
from backend.app.inventory import MaterialInventory


def test_job_exceeding_printer_build_volume_is_ineligible(
    shell_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def parse(self: object, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {
                "material": "PLA",
                "dimensions": {"x": 201.0, "y": 100.0, "z": 100.0},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    inventory = MaterialInventory()
    inventory.add_material(material_type="PLA", color="black", amount_grams=100)
    monkeypatch.setattr(jobs, "get_inventory_availability", lambda: inventory)
    monkeypatch.setattr(jobs, "get_printer_capabilities", lambda printer_id: {"id": printer_id, "buildVolume": {"x": 200, "y": 200, "z": 200}})
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"requirements": {"material": {"color": "black", "amountGrams": 100}}},
    )
    assert created.status_code == 201

    result = shell_client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "build_volume_exceeded" in [
        failure["code"] for failure in result.json()["failures"]
    ]
