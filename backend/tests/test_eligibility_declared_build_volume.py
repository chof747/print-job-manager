from fastapi.testclient import TestClient


def test_declared_build_volume_blocks_undersized_printer_after_real_import(
    client: TestClient,
) -> None:
    printer = client.put(
        "/api/v1/printers/printer-1",
        json={"enclosure": True, "buildVolume": {"x": 200, "y": 200, "z": 200}},
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
        json={
            "material": "PLA",
            "requirements": {"buildVolume": {"x": 201, "y": 100, "z": 100}},
        },
    )
    assert created.status_code == 201

    result = client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility",
        json={"printer": {"id": "printer-1"}},
    )
    assert result.status_code == 200
    assert result.json()["blocked"] is True
    assert "build_volume_exceeded" in [
        failure["code"] for failure in result.json()["failures"]
    ]
