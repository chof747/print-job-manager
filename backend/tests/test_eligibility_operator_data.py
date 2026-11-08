from fastapi.testclient import TestClient


def test_operator_catalog_data_is_available_to_later_eligibility_requests(
    client: TestClient,
) -> None:
    printer = client.put(
        "/api/v1/printers/printer-1",
        json={"enclosure": True},
    )
    assert printer.status_code in (200, 201)
    material = client.post(
        "/api/v1/inventory/materials",
        json={"materialType": "PLA", "color": "black", "amountGrams": 100},
    )
    assert material.status_code == 201
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={
            "material": "PLA",
            "requirements": {
                "enclosure": True,
                "material": {"color": "black", "amountGrams": 100},
            },
        },
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is True
    assert result.json()["failures"] == []
