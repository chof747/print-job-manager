from fastapi.testclient import TestClient


def test_import_review_survives_a_fresh_service(client: TestClient) -> None:
    from backend.app.api.v1 import jobs

    imported = client.post(
        "/api/v1/import",
        files={
            "file": (
                "cube.gcode",
                b"; filament_type = PLA\n;TIME:bad\nG28\n",
                "text/x.gcode",
            )
        },
    )
    assert imported.status_code == 201
    review = imported.json()
    assert review["extractedMetadata"]["material"] == "PLA"
    assert review["provenance"]["material"]["sourceKey"] == "filament_type"
    assert review["missingPlanningValues"] == []
    assert {"code": "malformed_metadata", "sourceKey": "TIME"} in review["diagnostics"]

    jobs.import_service = jobs.ImportService()
    restored = client.get(f"/api/v1/import/{review['artifact']['id']}")

    assert restored.status_code == 200
    assert restored.json() == review
