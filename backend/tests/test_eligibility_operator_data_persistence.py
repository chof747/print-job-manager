import importlib

from fastapi.testclient import TestClient


def test_operator_catalog_data_survives_fresh_application_wiring(client: TestClient) -> None:
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
        json={
            "material": "PLA",
            "requirements": {
                "enclosure": True,
                "material": {"color": "black", "amountGrams": 100},
            },
        },
    )
    assert created.status_code == 201
    url = f"/api/v1/jobs/{created.json()['id']}/eligibility"
    before = client.post(url, json={"printer": {"id": "printer-1"}})
    assert before.status_code == 200
    assert before.json()["eligible"] is True

    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs

    importlib.reload(jobs)
    importlib.reload(v1)
    importlib.reload(main)
    with TestClient(main.app) as fresh_client:
        after = fresh_client.post(url, json={"printer": {"id": "printer-1"}})

    assert after.status_code == 200
    assert after.json()["eligible"] is True
    assert after.json()["failures"] == []
