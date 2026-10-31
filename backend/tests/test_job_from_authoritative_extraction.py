import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_fresh_service_creates_job_from_extraction_not_legacy_artifact_copy(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={
            "file": ("cube.gcode", b"; filament_type = PLA\nG28\n", "text/x.gcode")
        },
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]

    # A legacy duplicate must not be authoritative if it still exists.
    with database.engine.begin() as connection:
        artifacts = sa.Table("artifacts", sa.MetaData(), autoload_with=connection)
        if "snapshot_material" in artifacts.c:
            connection.execute(
                artifacts.update()
                .where(artifacts.c.id == artifact_id)
                .values(snapshot_material="PETG")
            )

    jobs.import_service = jobs.ImportService()
    created = client.post(f"/api/v1/import/{artifact_id}/jobs", json={})
    assert created.status_code == 201
    assert created.json()["executionData"]["material"] == "PLA"
