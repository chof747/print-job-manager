from fastapi.testclient import TestClient


def test_import_retains_extraction_and_parser_identity_in_a_fresh_repository(
    client: TestClient,
) -> None:
    from backend.app.api.v1.jobs import SqlAlchemyImportRepository

    response = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
    )
    assert response.status_code == 201
    artifact_id = response.json()["artifact"]["id"]

    first = SqlAlchemyImportRepository().load_import(artifact_id)
    second = SqlAlchemyImportRepository().load_import(artifact_id)

    assert first is not None
    assert second is not None
    extraction = first["extraction"]
    assert isinstance(extraction, dict)
    assert isinstance(extraction["id"], str) and extraction["id"]
    assert isinstance(extraction["parser"], str) and extraction["parser"]
    assert second["extraction"] == extraction
