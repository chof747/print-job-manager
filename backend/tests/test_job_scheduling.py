from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


@pytest.mark.parametrize("mode", ["preferred", "required"])
@pytest.mark.parametrize("printer_id", ["", "   "])
def test_printer_assignment_rejects_blank_printer_ids_without_changing_job(
    shell_client: TestClient, mode: str, printer_id: str
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    job = created.json()

    response = shell_client.patch(
        f"/api/v1/jobs/{job['id']}/scheduling",
        json={
            "expectedVersion": job["version"],
            "priority": 10,
            "printerAssignment": {"mode": mode, "printerId": printer_id},
        },
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{job['id']}").json() == job


@pytest.mark.parametrize(
    "changes",
    [
        {"priority": None},
        {"tags": None},
        {"tags": ["urgent", "urgent"]},
        {"priority": 2147483648},
        {"tags": ["x" * 256]},
        {"printerAssignment": {"mode": "required", "printerId": "x" * 256}},
    ],
    ids=["null-priority", "null-tags", "duplicate-tags", "priority-overflow", "long-tag", "long-printer-id"],
)
def test_invalid_scheduling_inputs_are_rejected_without_changing_the_job(
    client: TestClient, changes: dict[str, object]
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    job = created.json()

    response = client.patch(
        f"/api/v1/jobs/{job['id']}/scheduling",
        json={**changes, "expectedVersion": job["version"]},
    )

    assert response.status_code == 422
    assert client.get(f"/api/v1/jobs/{job['id']}").json() == job


def test_concurrent_postgresql_scheduling_edits_reject_one_stale_write(
    client: TestClient,
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    job = created.json()
    start = Barrier(2, timeout=10)

    def update(priority: int):
        start.wait()
        return client.patch(
            f"/api/v1/jobs/{job['id']}/scheduling",
            json={"priority": priority, "expectedVersion": job["version"]},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(update, (10, 20)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    successful = next(response.json() for response in responses if response.status_code == 200)
    conflict = next(response.json() for response in responses if response.status_code == 409)
    assert conflict["detail"] == {"code": "version_conflict", "currentVersion": successful["version"]}
    assert client.get(f"/api/v1/jobs/{job['id']}").json() == successful


def test_required_printer_assignment_persists_after_a_fresh_repository_load(
    client: TestClient,
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    assignment = {"mode": "required", "printerId": "printer-mk4"}

    updated = client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"printerAssignment": assignment, "expectedVersion": created.json()["version"]},
    )
    jobs.import_service = jobs.ImportService()
    detail = client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["printerAssignment"] == assignment


def test_postgresql_scheduling_fields_persist_after_a_fresh_repository_load(
    client: TestClient,
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    scheduling_data = {
        "priority": 25,
        "dueDate": "2026-11-07",
        "notes": "Deliver before the trade show.",
        "tags": ["customer-order", "urgent"],
        "printerAssignment": {"mode": "preferred", "printerId": "printer-mk4"},
    }

    updated = client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={**scheduling_data, "expectedVersion": created.json()["version"]},
    )

    jobs.import_service = jobs.ImportService()
    detail = client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"] == scheduling_data


def test_queued_job_scheduling_update_requires_an_expected_version(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": 10},
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == created.json()


def test_newly_queued_job_detail_exposes_numeric_priority_zero_by_default(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["priority"] == 0
    assert isinstance(detail.json()["schedulingData"]["priority"], int)


def test_queued_job_due_date_update_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"dueDate": "2026-11-07", "expectedVersion": created.json()["version"]},
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["dueDate"] == "2026-11-07"


def test_queued_job_notes_update_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={
            "notes": "Deliver before the trade show.",
            "expectedVersion": created.json()["version"],
        },
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["notes"] == "Deliver before the trade show."


def test_queued_job_tags_update_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={
            "tags": ["customer-order", "urgent"],
            "expectedVersion": created.json()["version"],
        },
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["tags"] == ["customer-order", "urgent"]


def test_queued_job_preferred_printer_assignment_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={
            "printerAssignment": {"mode": "preferred", "printerId": "printer-mk4"},
            "expectedVersion": created.json()["version"],
        },
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["printerAssignment"] == {
        "mode": "preferred",
        "printerId": "printer-mk4",
    }


def test_queued_job_required_printer_assignment_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )
    assignment = {"mode": "required", "printerId": "printer-mk4"}

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"printerAssignment": assignment, "expectedVersion": created.json()["version"]},
    )

    assert updated.status_code == 200
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")
    assert detail.json()["schedulingData"]["printerAssignment"] == assignment


def test_queued_job_positive_priority_update_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": 25, "expectedVersion": created.json()["version"]},
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["priority"] == 25


def test_queued_job_negative_priority_update_is_returned_by_job_detail(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": -10, "expectedVersion": created.json()["version"]},
    )
    detail = shell_client.get(f"/api/v1/jobs/{created.json()['id']}")

    assert updated.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["schedulingData"]["priority"] == -10


def test_queued_job_rejects_artifact_changes_through_the_scheduling_api(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"executionData": {"artifactRef": "sha256:replacement"}},
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, executionData is immutable after queueing; "
        "create a replacement job instead"
    )


def test_queued_job_rejects_direct_artifact_reference_changes_through_scheduling_api(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={
            "artifactRef": "sha256:replacement",
            "expectedVersion": created.json()["version"],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, executionData is immutable after queueing; "
        "create a replacement job instead"
    )


def test_queued_job_rejects_direct_material_changes_through_scheduling_api(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"material": "PETG", "expectedVersion": created.json()["version"]},
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == created.json()


@pytest.mark.parametrize(
    ("field", "value"),
    [("checksum", "replacement"), ("extractedMetadata", {"material": "PETG"})],
)
def test_queued_job_rejects_direct_execution_fields_atomically(
    shell_client: TestClient, field: str, value: object
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={field: value, "priority": 10, "expectedVersion": created.json()["version"]},
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == created.json()


def test_scheduling_update_rejects_unrecognized_fields_without_applying_changes(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={
            "printerRequirements": {"nozzleDiameter": 0.8},
            "priority": 10,
            "expectedVersion": created.json()["version"],
        },
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == created.json()


def test_queued_job_scheduling_update_is_visible_in_queue_projection(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": 10, "expectedVersion": created.json()["version"]},
    )
    queue = shell_client.get("/api/v1/queue")

    assert updated.status_code == 200
    assert queue.status_code == 200
    assert queue.json()["jobs"][0]["schedulingData"]["priority"] == 10


def test_queued_job_scheduling_update_advances_version_and_rejects_a_stale_write(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    assert created.json()["version"] == 0

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": 10, "expectedVersion": 0},
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 1

    stale_update = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": 20, "expectedVersion": 0},
    )

    assert stale_update.status_code == 409
    assert stale_update.json() == {
        "detail": {"code": "version_conflict", "currentVersion": 1}
    }


def test_queued_job_priority_can_be_changed_to_a_negative_integer_and_is_reflected_in_projections(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"priority": -10, "expectedVersion": created.json()["version"]},
    )

    assert updated.status_code == 200
    assert updated.json()["schedulingData"] == {"priority": -10}
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == updated.json()
    assert shell_client.get("/api/v1/queue").json() == {"jobs": [updated.json()]}


def test_queued_job_scheduling_fields_can_be_updated_together_and_are_reflected_in_projections(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    scheduling_data = {
        "priority": 25,
        "dueDate": "2026-11-07",
        "notes": "Deliver before the trade show.",
        "tags": ["customer-order", "urgent"],
        "printerAssignment": {"mode": "preferred", "printerId": "printer-mk4"},
    }
    updated = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={**scheduling_data, "expectedVersion": created.json()["version"]},
    )

    assert updated.status_code == 200
    assert updated.json()["schedulingData"] == scheduling_data
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == updated.json()
    assert shell_client.get("/api/v1/queue").json() == {"jobs": [updated.json()]}


def test_queued_job_rejects_execution_data_changes_through_the_scheduling_api(
    shell_client: TestClient,
) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    )

    response = shell_client.patch(
        f"/api/v1/jobs/{created.json()['id']}/scheduling",
        json={"executionData": {"material": "PETG"}},
    )

    assert response.status_code == 422
    assert shell_client.get(f"/api/v1/jobs/{created.json()['id']}").json() == created.json()
