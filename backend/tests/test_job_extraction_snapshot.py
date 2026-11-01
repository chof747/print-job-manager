import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_queued_job_snapshot_records_authoritative_extraction_not_legacy_copy(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"; filament_type = PLA\nG28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]

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
    detail = client.get(f"/api/v1/jobs/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["executionData"]["material"] == "PLA"
    assert detail.json()["parsedMetadataSnapshot"]["extractedMetadata"]["material"] == "PLA"
