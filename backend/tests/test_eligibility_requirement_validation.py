from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_job_rejects_non_boolean_enclosure_requirement(shell_client: TestClient) -> None:
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
        json={"material": "PLA", "requirements": {"enclosure": "not-a-boolean"}},
    )

    assert created.status_code == 422
