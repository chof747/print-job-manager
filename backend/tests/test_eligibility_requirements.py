from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_job_preserves_enclosure_requirement_separately_from_scheduling_preferences(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA", "requirements": {"enclosure": True}},
    )
    assert created.status_code == 201
    job = created.json()
    assert job["executionData"]["requirements"]["enclosure"] is True
    assert "requirements" not in job["schedulingData"]


def test_enclosure_requirement_survives_persistent_job_reload(client: TestClient) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "requirements": {"enclosure": True}},
    )
    assert created.status_code == 201

    reloaded = client.get(f"/api/v1/jobs/{created.json()['id']}")
    assert reloaded.status_code == 200
    assert reloaded.json()["executionData"]["requirements"]["enclosure"] is True
