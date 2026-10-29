import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


@pytest.mark.parametrize(
    ("field", "value", "preserved"),
    [
        ("nozzleDiameter", 0.4, True),
        ("bedTemperature", 60, False),
        ("customProfile", "draft", False),
        ("customSettings", {"nested": [1, 2]}, False),
    ],
)
def test_legacy_planning_migration(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    preserved: bool,
) -> None:
    from backend.app.config import get_settings

    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )
    schema = f"test_planning_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_url)
    get_settings.cache_clear()
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", scoped_url)
    engine = sa.create_engine(scoped_url)
    digest = "f" * 64
    legacy_id = f"sha256:{digest}"
    snapshot = {"missingPlanningValues": ["material", field], "diagnostics": []}
    execution = {"artifactRef": legacy_id, "material": "PLA", field: value}
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                VALUES (:id, :digest, :id, 'cube.gcode', CAST(:snapshot AS jsonb))"""),
                {"id": legacy_id, "digest": digest, "snapshot": json.dumps(snapshot)},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs
                (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                VALUES ('legacy-job', :id, CAST(:snapshot AS jsonb), 'ready',
                CAST(:execution AS jsonb), '{"priority": 0}'::jsonb)"""),
                {
                    "id": legacy_id,
                    "snapshot": json.dumps(snapshot),
                    "execution": json.dumps(execution),
                },
            )
        command.upgrade(config, "20261028_0009")
        assert not sa.inspect(engine).has_table("job_planning_facts")
        command.upgrade(config, "20261028_0010")
        assert not sa.inspect(engine).has_table("legacy_artifact_identifiers")
        command.upgrade(config, "head")
        from sqlalchemy.orm import Session

        from backend.app.persistence.models import JobRecord

        with Session(engine) as session:
            record = session.get(JobRecord, "legacy-job")
            assert record is not None
            if preserved:
                assert record.execution_data[field] == value
            else:
                assert field not in record.execution_data
            assert not sa.inspect(engine).has_table("job_planning_facts")
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()
