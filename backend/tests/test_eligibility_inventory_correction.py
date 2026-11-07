from fastapi.testclient import TestClient


def test_correcting_inventory_resource_recalculates_eligibility(client: TestClient) -> None:
    assert client.put("/api/v1/printers/printer-1", json={"enclosure": True}).status_code in (
        200,
        201,
    )
    material = client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 100},
    )
    assert material.status_code == 201
    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 40},
    ).status_code == 201
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "requirements": {"material": {"color": "black", "amountGrams": 80}}},
    )
    assert created.status_code == 201
    url = f"/api/v1/jobs/{created.json()['id']}/eligibility"
    before = client.post(url, json={"printer": {"id": "printer-1"}})
    assert before.status_code == 200
    assert before.json()["eligible"] is True

    resource_id = material.json()["id"]
    corrected = client.patch(
        f"/api/v1/inventory/materials/{resource_id}", json={"amountGrams": 30}
    )
    assert corrected.status_code == 200
    after = client.post(url, json={"printer": {"id": "printer-1"}})
    assert after.status_code == 200
    assert after.json()["blocked"] is True
    assert "inventory_material_unavailable" in [
        failure["code"] for failure in after.json()["failures"]
    ]
