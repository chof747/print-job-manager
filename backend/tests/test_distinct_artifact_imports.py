from fastapi.testclient import TestClient


def test_identical_artifact_uploads_keep_separate_import_contexts(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs

    first = client.post(
        "/api/v1/import",
        files={"file": ("first.gcode", b"G28\n", "text/x.gcode")},
    )
    second = client.post(
        "/api/v1/import",
        files={"file": ("second.gcode", b"G28\n", "application/octet-stream")},
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["artifact"]["id"] == second.json()["artifact"]["id"]
    first_id = first.json()["import"]["id"]
    second_id = second.json()["import"]["id"]
    assert first_id != second_id

    jobs.import_service = jobs.ImportService()
    first_review = client.get(f"/api/v1/import/{first_id}")
    second_review = client.get(f"/api/v1/import/{second_id}")
    assert first_review.status_code == second_review.status_code == 200
    assert first_review.json()["artifact"]["id"] == second_review.json()["artifact"]["id"]
    assert first_review.json()["artifact"]["filename"] == "first.gcode"
    assert first_review.json()["artifact"]["mediaType"] == "text/x.gcode"
    assert second_review.json()["artifact"]["filename"] == "second.gcode"
    assert second_review.json()["artifact"]["mediaType"] == "application/octet-stream"
