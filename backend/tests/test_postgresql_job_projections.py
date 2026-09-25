import hashlib
import importlib
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


@pytest.fixture
def unmigrated_postgresql_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_unmigrated_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_database_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_database_url)

    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(job_repository)
    importlib.reload(jobs)
    importlib.reload(v1)
    reloaded_main = importlib.reload(main)

    try:
        with TestClient(reloaded_main.app, raise_server_exceptions=False) as client:
            yield client
    finally:
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_unmigrated_postgresql_persistence_does_not_fall_back_to_memory(
    unmigrated_postgresql_client: TestClient,
) -> None:
    imported = unmigrated_postgresql_client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )
    queue = unmigrated_postgresql_client.get("/api/v1/queue")

    assert imported.status_code >= 500
    assert queue.status_code >= 500


def test_import_to_ready_job_persists_the_artifact_snapshot_and_creation_history(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_transaction_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_database_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_database_url)

    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(job_repository)
    importlib.reload(jobs)
    importlib.reload(v1)
    reloaded_main = importlib.reload(main)

    alembic_config = Config(str(repo_root / "backend" / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(repo_root / "backend" / "alembic")
    )
    alembic_config.set_main_option("sqlalchemy.url", scoped_database_url)
    command.upgrade(alembic_config, "head")
    content = b"; material: PLA\nG28\n"
    try:
        with TestClient(reloaded_main.app, raise_server_exceptions=False) as client:
            imported = client.post(
                "/api/v1/import",
                files={"file": ("calibration-cube.gcode", content, "text/x.gcode")},
            )
            created = client.post(
                f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
                json={"material": "PLA"},
            )

        assert created.status_code == 201
        job = created.json()
        with admin_engine.connect() as connection:
            connection.execute(sa.text(f'SET search_path TO "{schema}"'))
            artifact = (
                connection.execute(sa.text("SELECT id, sha256 FROM artifacts"))
                .mappings()
                .one()
            )
            persisted_job = (
                connection.execute(
                    sa.text(
                        "SELECT artifact_ref, parsed_metadata_snapshot, state FROM jobs "
                        "WHERE id = :job_id"
                    ),
                    {"job_id": job["id"]},
                )
                .mappings()
                .one()
            )
            history = (
                connection.execute(
                    sa.text(
                        "SELECT job_id, state FROM job_history WHERE job_id = :job_id"
                    ),
                    {"job_id": job["id"]},
                )
                .mappings()
                .one()
            )

        assert artifact == {
            "id": imported.json()["artifact"]["id"],
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        assert persisted_job == {
            "artifact_ref": artifact["id"],
            "parsed_metadata_snapshot": {
                "missingPlanningValues": ["material"],
                "diagnostics": [],
            },
            "state": "ready",
        }
        assert history == {"job_id": job["id"], "state": "ready"}
    finally:
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_fresh_backend_creates_a_job_from_a_persisted_import_with_its_metadata_snapshot(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_import_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_database_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_database_url)

    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(job_repository)
    importlib.reload(jobs)
    importlib.reload(v1)
    reloaded_main = importlib.reload(main)

    def parse_with_metadata(
        self: jobs.GcodeParser, *, artifact_id: str, content: bytes
    ) -> dict[str, object]:
        return {
            "extractedMetadata": {"estimatedDuration": 3600},
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse_with_metadata)

    alembic_config = Config(str(repo_root / "backend" / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(repo_root / "backend" / "alembic")
    )
    alembic_config.set_main_option("sqlalchemy.url", scoped_database_url)
    command.upgrade(alembic_config, "head")
    try:
        with TestClient(reloaded_main.app, raise_server_exceptions=False) as client:
            imported = client.post(
                "/api/v1/import",
                files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
            )

        assert imported.status_code == 201
        artifact_id = imported.json()["artifact"]["id"]

        importlib.reload(jobs)
        importlib.reload(v1)
        restarted_main = importlib.reload(main)
        with TestClient(
            restarted_main.app, raise_server_exceptions=False
        ) as restarted_client:
            created = restarted_client.post(
                f"/api/v1/import/{artifact_id}/jobs", json={}
            )

            assert created.status_code == 201
            detail = restarted_client.get(f"/api/v1/jobs/{created.json()['id']}")

        assert detail.status_code == 200
        assert detail.json()["executionData"] == {
            "artifactRef": artifact_id,
            "material": None,
            "extractedMetadata": {"estimatedDuration": 3600},
        }
    finally:
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_created_job_is_loaded_by_fresh_backend_detail_and_queue_projections(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", database_url)

    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(job_repository)
    importlib.reload(jobs)
    importlib.reload(v1)
    reloaded_main = importlib.reload(main)

    alembic_config = Config(str(repo_root / "backend" / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(repo_root / "backend" / "alembic")
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    try:
        with TestClient(reloaded_main.app, raise_server_exceptions=False) as client:
            imported = client.post(
                "/api/v1/import",
                files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
            )
            created = client.post(
                f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
                json={"material": "PLA"},
            )

        assert created.status_code == 201
        created_job = created.json()

        importlib.reload(jobs)
        importlib.reload(v1)
        restarted_main = importlib.reload(main)
        with TestClient(
            restarted_main.app, raise_server_exceptions=False
        ) as restarted_client:
            detail = restarted_client.get(f"/api/v1/jobs/{created_job['id']}")
            queue = restarted_client.get("/api/v1/queue")

        assert detail.json() == created_job
        assert queue.json() == {"jobs": [created_job]}
    finally:
        command.downgrade(alembic_config, "base")


def test_default_api_import_is_isolated_after_projection_database_cleanup(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/import",
        files={"file": ("calibration-cube.gcode", b"G28\n", "text/x.gcode")},
    )

    assert response.status_code == 201
