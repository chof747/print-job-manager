from fastapi.testclient import TestClient


def test_original_upload_context_survives_a_fresh_repository(
    client: TestClient,
) -> None:
    from backend.app.api.v1.jobs import SqlAlchemyImportRepository

    response = client.post(
        "/api/v1/import",
        files={"file": ("original.gcode", b"G28\n", "text/x-gcode")},
    )
    assert response.status_code == 201
    artifact_id = response.json()["artifact"]["id"]

    persisted = SqlAlchemyImportRepository().load_import(artifact_id)
    assert persisted is not None
    assert persisted["filename"] == "original.gcode"
    assert persisted["mediaType"] == "text/x-gcode"
