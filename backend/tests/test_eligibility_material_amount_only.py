from fastapi.testclient import TestClient


def test_amount_only_requirement_checks_stock_without_restricting_color(client: TestClient) -> None:
    assert client.put("/api/v1/printers/printer-1", json={"enclosure": True}).status_code in (200, 201)
    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "red", "amountGrams": 50},
    ).status_code == 201
    imported = client.post(
        "/api/v1/import", files={"file": ("part.gcode", b"G28\n", "text/x-gcode")}
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "requirements": {"material": {"amountGrams": 100}}},
    )
    assert created.status_code == 201

    url = f"/api/v1/jobs/{created.json()['id']}/eligibility"
    blocked = client.post(url, json={"printer": {"id": "printer-1"}})
    assert blocked.status_code == 200
    assert blocked.json()["blocked"] is True
    assert {"code": "inventory_material_unavailable"} in blocked.json()["failures"]

    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "blue", "amountGrams": 100},
    ).status_code == 201
    eligible = client.post(url, json={"printer": {"id": "printer-1"}})
    assert eligible.status_code == 200
    assert eligible.json()["eligible"] is True
