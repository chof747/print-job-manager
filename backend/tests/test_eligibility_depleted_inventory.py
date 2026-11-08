import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("requirements", [{}, {"material": {"color": "black"}}])
def test_depleted_matching_material_does_not_make_job_eligible(
    client: TestClient, requirements: dict
) -> None:
    assert client.put("/api/v1/printers/printer-1", json={"enclosure": True}).status_code in (200, 201)
    material = client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 100},
    )
    assert material.status_code == 201
    assert client.patch(
        f"/api/v1/inventory/materials/{material.json()['id']}", json={"amountGrams": 0}
    ).status_code == 200
    imported = client.post(
        "/api/v1/import", files={"file": ("part.gcode", b"G28\n", "text/x-gcode")}
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "requirements": requirements},
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )
    assert result.status_code == 200
    assert result.json()["blocked"] is True
    assert {"code": "inventory_material_unavailable"} in result.json()["failures"]
