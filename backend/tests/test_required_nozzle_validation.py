import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_required_nozzle_rejects_invalid_values_and_persists_valid_input(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA"},
            "missingPlanningValues": ["nozzleDiameter"],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import", files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")}
    )
    assert imported.status_code == 201
    import_id = imported.json()["import"]["id"]

    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        for value in ("not-a-number", "0", "-0.4", "NaN", "Infinity"):
            response = error_client.post(
                f"/api/v1/import/{import_id}/jobs", json={"nozzleDiameter": value}
            )
            assert response.status_code == 422, f"{value!r} was not rejected"

        created = error_client.post(
            f"/api/v1/import/{import_id}/jobs", json={"nozzleDiameter": "0.4"}
        )
    assert created.status_code == 201
    assert created.json()["executionData"]["nozzleDiameter"] == 0.4
    with database.engine.connect() as connection:
        job_table = sa.Table("jobs", sa.MetaData(), autoload_with=connection)
        assert isinstance(job_table.c.nozzle_diameter.type, (sa.Float, sa.Numeric))
        assert connection.scalar(
            sa.select(job_table.c.nozzle_diameter).where(job_table.c.id == created.json()["id"])
        ) == 0.4
