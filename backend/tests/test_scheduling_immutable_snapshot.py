from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_scheduling_update_explains_that_parsed_metadata_snapshot_is_immutable(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("job.gcode", b"; filament_type = PLA\nG28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={}
    ).json()

    response = shell_client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={
            "parsedMetadataSnapshot": {"extractedMetadata": {"material": "PETG"}},
            "priority": 10,
            "expectedVersion": created["version"],
        },
    )

    assert response.status_code == 422
    message = " ".join(error["msg"] for error in response.json()["detail"])
    assert "immutable" in message.lower() or "replacement job" in message.lower()
    assert shell_client.get(f"/api/v1/jobs/{created['id']}").json() == created


def test_scheduling_update_explains_that_artifact_filename_is_immutable(
    shell_client: TestClient,
) -> None:
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
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={"material": "PLA"}
    ).json()

    response = shell_client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={"artifactFilename": "replacement.gcode", "expectedVersion": created["version"]},
    )

    assert response.status_code == 422
    message = " ".join(error["msg"] for error in response.json()["detail"])
    assert "immutable" in message.lower() or "replacement job" in message.lower()
    assert shell_client.get(f"/api/v1/jobs/{created['id']}").json() == created


def test_scheduling_update_explains_that_estimated_duration_is_immutable(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("job.gcode", b";TIME:3600\n; filament_type = PLA\nG28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={}
    ).json()

    response = shell_client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={"estimatedDuration": 7200, "priority": 10, "expectedVersion": created["version"]},
    )

    assert response.status_code == 422
    message = " ".join(error["msg"] for error in response.json()["detail"])
    assert "immutable" in message.lower() or "replacement job" in message.lower()
    assert shell_client.get(f"/api/v1/jobs/{created['id']}").json() == created
