import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_matching_printer_and_available_material_are_eligible(
    shell_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Inventory:
        def is_available(self, material: str) -> bool:
            return material == "PLA"

    monkeypatch.setattr(jobs, "get_inventory_availability", lambda: Inventory(), raising=False)
    monkeypatch.setattr(jobs, "get_printer_capabilities", lambda printer_id: {"id": printer_id, "enclosure": True})
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
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["failures"] == []
