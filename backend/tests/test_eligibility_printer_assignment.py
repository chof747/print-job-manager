import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs
from backend.app.inventory import MaterialInventory


def test_required_printer_blocks_mismatch_but_preferred_does_not(
    shell_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = MaterialInventory()
    inventory.add_material(material_type="PLA", color="black", amount_grams=100)
    monkeypatch.setattr(jobs, "get_inventory_availability", lambda: inventory)
    monkeypatch.setattr(
        jobs,
        "get_printer_capabilities",
        lambda printer_id: {"id": "printer-2", "enclosure": True}
        if printer_id == "printer-2"
        else None,
        raising=False,
    )
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
        json={"material": "PLA", "requirements": {"material": {"color": "black", "amountGrams": 100}}},
    )
    assert created.status_code == 201
    job = created.json()
    url = f"/api/v1/jobs/{job['id']}"
    preferred = shell_client.patch(
        f"{url}/scheduling",
        json={"expectedVersion": job["version"], "printerAssignment": {"mode": "preferred", "printerId": "printer-1"}},
    )
    assert preferred.status_code == 200
    result = shell_client.post(f"{url}/eligibility", json={"printer": {"id": "printer-2"}})
    assert result.status_code == 200
    assert result.json()["eligible"] is True

    required = shell_client.patch(
        f"{url}/scheduling",
        json={"expectedVersion": preferred.json()["version"], "printerAssignment": {"mode": "required", "printerId": "printer-1"}},
    )
    assert required.status_code == 200
    result = shell_client.post(f"{url}/eligibility", json={"printer": {"id": "printer-2"}})
    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "required_printer_mismatch" in [
        failure["code"] for failure in result.json()["failures"]
    ]
