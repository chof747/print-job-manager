import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


def test_scheduling_edits_survive_downgrade_and_upgrade(
    client: TestClient, repo_root: Path
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("job.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    ).json()
    scheduling = {
        "priority": -10,
        "dueDate": "2026-11-07",
        "notes": "Important delivery",
        "tags": ["urgent", "customer"],
        "printerAssignment": {"mode": "required", "printerId": "printer-mk4"},
    }
    updated = client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={**scheduling, "expectedVersion": created["version"]},
    )
    assert updated.status_code == 200

    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["PRINT_JOB_MANAGER_DATABASE_URL"])
    command.downgrade(config, "20260925_0002")
    command.upgrade(config, "head")

    detail = client.get(f"/api/v1/jobs/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["schedulingData"] == scheduling


def test_stale_scheduling_edit_is_rejected_after_version_migration_roundtrip(
    client: TestClient, repo_root: Path
) -> None:
    imported = client.post(
        "/api/v1/import",
        files={"file": ("job.gcode", b"G28\n", "text/x.gcode")},
    )
    created = client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
        json={"material": "PLA"},
    ).json()
    updated = client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={"priority": 10, "expectedVersion": created["version"]},
    )
    assert updated.status_code == 200

    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["PRINT_JOB_MANAGER_DATABASE_URL"])
    command.downgrade(config, "20261028_0003")
    command.upgrade(config, "head")

    stale = client.patch(
        f"/api/v1/jobs/{created['id']}/scheduling",
        json={"priority": 20, "expectedVersion": created["version"]},
    )
    assert stale.status_code == 409
    assert client.get(f"/api/v1/jobs/{created['id']}").json()["schedulingData"]["priority"] == 10
