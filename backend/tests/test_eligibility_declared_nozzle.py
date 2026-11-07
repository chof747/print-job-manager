from fastapi.testclient import TestClient


def test_declared_nozzle_is_enforced_when_import_does_not_extract_one(
    client: TestClient,
) -> None:
    printer = client.put(
        "/api/v1/printers/printer-1",
        json={"enclosure": True, "nozzleDiameter": 0.6},
    )
    assert printer.status_code in (200, 201)
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
        json={"material": "PLA", "nozzleDiameter": 0.4},
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )

    assert result.status_code == 200
    assert result.json()["eligible"] is False
    assert "nozzle_diameter_mismatch" in [
        failure["code"] for failure in result.json()["failures"]
    ]
