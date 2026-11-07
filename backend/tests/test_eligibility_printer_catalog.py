from importlib import import_module

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs
from backend.app.inventory import MaterialInventory


def test_eligibility_uses_printer_catalog_instead_of_caller_capabilities(
    shell_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    printers = import_module("backend.app.printers").PrinterCatalog()
    printers.add_printer(printer_id="printer-1", enclosure=True)
    monkeypatch.setattr(jobs, "get_printer_capabilities", printers.get_capabilities)
    inventory = MaterialInventory()
    inventory.add_material(material_type="PLA", color="black", amount_grams=100)
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
        json={
            "material": "PLA",
            "requirements": {
                "enclosure": True,
                "material": {"color": "black", "amountGrams": 100},
            },
        },
    )
    assert created.status_code == 201

    result = shell_client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1", "enclosure": False}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["failures"] == []
