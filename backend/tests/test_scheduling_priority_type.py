from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_boolean_priority_is_rejected_without_changing_the_job(shell_client: TestClient) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("job.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    ).json()

    response = shell_client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={"priority": True, "expectedVersion": created["version"]},
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created['id']}").json() == created
