import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_migration_rejects_unsupported_legacy_priority_without_discarding_it(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.config import get_settings

    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )
    schema = f"test_priority_invalid_{uuid4().hex}"
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
    digest = "a" * 64
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                VALUES (:id, :digest, :id, 'cube.gcode',
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb)"""),
                {"id": f"sha256:{digest}", "digest": digest},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs
                (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                VALUES ('legacy-job', :artifact,
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb,
                'ready', '{"material": "PLA"}'::jsonb, CAST(:scheduling AS jsonb))"""),
                {
                    "artifact": f"sha256:{digest}",
                    "scheduling": json.dumps({"priority": "urgent"}),
                },
            )
        command.upgrade(config, "20261028_0004")
        with pytest.raises((ValueError, sa.exc.DBAPIError)):
            command.upgrade(config, "20261028_0005")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("""SELECT text_value FROM job_data_nodes
                WHERE owner_id = 'legacy-job' AND field = 'scheduling' AND path = '/priority'""")
                ).scalar_one()
                == "urgent"
            )
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()


@pytest.mark.parametrize("priority", [2**31, 2**63])
def test_backfill_preserves_legacy_integer_priority_outside_32_bit_range(
    priority: int, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.config import get_settings

    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_priority_{uuid4().hex}"
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
    digest = "d" * 64
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                VALUES (:id, :digest, :id, 'cube.gcode',
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb)"""),
                {"id": f"sha256:{digest}", "digest": digest},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs
                (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                VALUES ('legacy-job', :artifact,
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb,
                'ready', '{"material": "PLA"}'::jsonb,
                CAST(:scheduling AS jsonb))"""),
                {
                    "artifact": f"sha256:{digest}",
                    "scheduling": f'{{"priority": {priority}}}',
                },
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT priority FROM jobs WHERE id = 'legacy-job'")
                ).scalar_one()
                == priority
            )
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()
