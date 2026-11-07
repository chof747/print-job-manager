from fastapi.testclient import TestClient


def test_type_only_material_requirement_matches_available_stock_of_that_type(
    client: TestClient,
) -> None:
    assert client.put("/api/v1/printers/printer-1", json={"enclosure": True}).status_code in (
        200,
        201,
    )
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
        json={"material": "PLA"},
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["failures"] == []
