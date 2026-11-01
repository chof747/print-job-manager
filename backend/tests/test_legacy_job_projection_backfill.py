import importlib
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


def test_legacy_job_priority_and_history_survive_migration_and_restart(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_legacy_job_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = f"{database_url}?options=-csearch_path={schema}"
    original_url = os.environ.get("PRINT_JOB_MANAGER_DATABASE_URL")
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_url)
    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", scoped_url)
    engine = sa.create_engine(scoped_url)
    digest = "e" * 64
    legacy_ref = f"sha256:{digest}"
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                VALUES (:id, :digest, :id, 'cube.gcode',
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb)"""),
                {"id": legacy_ref, "digest": digest},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs
                (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                VALUES ('legacy-job', :artifact,
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb,
                'ready', jsonb_build_object('artifactRef', CAST(:execution_ref AS text),
                'material', 'PLA', 'artifactFilename', 'cube.gcode'), '{"priority": 17}'::jsonb)"""),
                {"artifact": legacy_ref, "execution_ref": legacy_ref},
            )
            connection.execute(
                sa.text("""INSERT INTO job_history (id, job_id, state)
                VALUES ('h1', 'legacy-job', 'created'), ('h2', 'legacy-job', 'ready')""")
            )
        command.upgrade(config, "head")

        importlib.reload(database)
        importlib.reload(models)
        importlib.reload(job_repository)
        importlib.reload(jobs)
        importlib.reload(v1)
        restarted_main = importlib.reload(main)
        with TestClient(restarted_main.app) as client:
            detail = client.get("/api/v1/jobs/legacy-job")
            queue = client.get("/api/v1/queue")
        assert detail.status_code == 200
        job = detail.json()
        assert job["state"] == "ready"
        assert job["executionData"] == {
            "artifactRef": digest,
            "artifactFilename": "cube.gcode",
            "material": "PLA",
        }
        assert job["schedulingData"] == {"priority": 17}
        assert queue.json() == {"jobs": [job]}
        with engine.connect() as connection:
            history = connection.execute(
                sa.text(
                    "SELECT id, state FROM job_history WHERE job_id = 'legacy-job' ORDER BY id"
                )
            ).all()
        assert history == [("h1", "created"), ("h2", "ready")]
    finally:
        database.engine.dispose()
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        if original_url is None:
            monkeypatch.delenv("PRINT_JOB_MANAGER_DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", original_url)
        app_config.get_settings.cache_clear()
        importlib.reload(database)
        importlib.reload(models)
        importlib.reload(job_repository)
        importlib.reload(jobs)
        importlib.reload(v1)
        importlib.reload(main)
