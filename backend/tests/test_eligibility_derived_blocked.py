from fastapi.testclient import TestClient


def test_pair_blocked_status_changes_with_printer_without_changing_job_state(
    client: TestClient,
) -> None:
    printer = client.put("/api/v1/printers/printer-1", json={"enclosure": False})
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
    job_url = f"/api/v1/jobs/{created.json()['id']}"

    blocked = client.post(f"{job_url}/eligibility", json={"printer": {"id": "printer-1"}})
    assert blocked.status_code == 200
    assert blocked.json()["blocked"] is True
    assert client.get(job_url).json()["state"] == "ready"

    updated = client.put("/api/v1/printers/printer-1", json={"enclosure": True})
    assert updated.status_code in (200, 201)
    unblocked = client.post(f"{job_url}/eligibility", json={"printer": {"id": "printer-1"}})
    assert unblocked.status_code == 200
    assert unblocked.json()["blocked"] is False
    assert client.get(job_url).json()["state"] == "ready"
