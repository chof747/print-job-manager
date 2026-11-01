import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_extracted_nozzle_is_an_immutable_typed_job_requirement(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "nozzleDiameter": 0.4},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"},
                "nozzleDiameter": {"parser": "prusa-family", "sourceKey": "nozzle_diameter"},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]
    jobs.import_service = jobs.ImportService()
    created = client.post(
        f"/api/v1/import/{artifact_id}/jobs", json={"nozzleDiameter": 0.8}
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["executionData"]["nozzleDiameter"] == 0.4

    with database.engine.begin() as connection:
        extraction = sa.Table("artifact_extractions", sa.MetaData(), autoload_with=connection)
        connection.execute(
            extraction.update().where(extraction.c.artifact_id == artifact_id).values(
                nozzle_diameter=0.6
            )
        )
        job_table = sa.Table("jobs", sa.MetaData(), autoload_with=connection)
        assert isinstance(job_table.c.nozzle_diameter.type, (sa.Float, sa.Numeric))
        assert connection.scalar(
            sa.select(job_table.c.nozzle_diameter).where(job_table.c.id == job_id)
        ) == 0.4

    jobs.import_service = jobs.ImportService()
    detail = client.get(f"/api/v1/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["executionData"]["nozzleDiameter"] == 0.4
