import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs
from backend.app.inventory import MaterialInventory


def test_enclosure_requirement_explains_ineligible_printer(
    shell_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "get_printer_capabilities", lambda printer_id: {"id": printer_id, "enclosure": False})
    inventory = MaterialInventory()
    inventory.add_material(material_type="PLA", color="", amount_grams=1)
    monkeypatch.setattr(jobs, "get_inventory_availability", lambda: inventory)
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
        json={"material": "PLA", "requirements": {"enclosure": True}},
    )
    assert created.status_code == 201

    result = shell_client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={
            "printer": {"id": "printer-1"},
        },
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "enclosure_required" in [failure["code"] for failure in result.json()["failures"]]
