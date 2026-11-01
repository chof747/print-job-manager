import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_job_preserves_printer_profile_after_extraction_changes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA", "printerProfile": "Original Prusa MK4"},
            "provenance": {
                "material": {"parser": "prusa-family", "sourceKey": "filament_type"},
                "printerProfile": {"parser": "prusa-family", "sourceKey": "printer_settings_id"},
            },
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import", files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")}
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]
    jobs.import_service = jobs.ImportService()
    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        created = error_client.post(f"/api/v1/import/{artifact_id}/jobs", json={})
    assert created.status_code == 201

    with database.engine.begin() as connection:
        extraction = sa.Table("artifact_extractions", sa.MetaData(), autoload_with=connection)
        connection.execute(
            extraction.update().where(extraction.c.artifact_id == artifact_id).values(
                printer_profile="Other printer"
            )
        )
    jobs.import_service = jobs.ImportService()
    detail = client.get(f"/api/v1/jobs/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["executionData"]["extractedMetadata"]["printerProfile"] == "Original Prusa MK4"
