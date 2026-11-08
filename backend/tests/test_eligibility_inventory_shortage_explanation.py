from fastapi.testclient import TestClient


def test_known_material_shortage_is_explained_as_unavailable(client: TestClient) -> None:
    assert client.put("/api/v1/printers/printer-1", json={"enclosure": True}).status_code in (
        200,
        201,
    )
    assert client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 50},
    ).status_code == 201
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "requirements": {"material": {"color": "black", "amountGrams": 100}}},
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["blocked"] is True
    codes = [failure["code"] for failure in result.json()["failures"]]
    assert "inventory_material_unavailable" in codes
