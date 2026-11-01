import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


def test_legacy_artifact_identifier_and_job_reference_are_converted(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_identifier_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_url)
    from backend.app.config import get_settings

    get_settings.cache_clear()
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", scoped_url)
    engine = sa.create_engine(scoped_url)
    digest = "b" * 64
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                VALUES (:legacy, :digest, :legacy, 'cube.gcode',
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb)"""),
                {"legacy": f"sha256:{digest}", "digest": digest},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs
                (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                VALUES ('legacy-job', :legacy,
                '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb,
                'ready', jsonb_build_object('artifactRef', CAST(:execution_ref AS text), 'material', 'PLA'),
                '{"priority": 7}'::jsonb)"""),
                {"legacy": f"sha256:{digest}", "execution_ref": f"sha256:{digest}"},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert (
                connection.execute(sa.text("SELECT id FROM artifacts")).scalar_one()
                == digest
            )
            assert (
                connection.execute(
                    sa.text("SELECT artifact_ref FROM jobs WHERE id = 'legacy-job'")
                ).scalar_one()
                == digest
            )
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()


def test_legacy_job_material_is_backfilled_as_a_typed_relational_fact(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    schema = f"test_backfill_{uuid4().hex}"
    admin_engine = sa.create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = f"{database_url}?options=-csearch_path={schema}"
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_url)
    from backend.app.config import get_settings

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
                sa.text("""INSERT INTO artifacts (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                    VALUES (:id, :digest, :id, 'cube.gcode', '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb)"""),
                {"id": f"sha256:{digest}", "digest": digest},
            )
            connection.execute(
                sa.text("""INSERT INTO jobs (id, artifact_ref, parsed_metadata_snapshot, state, execution_data, scheduling_data)
                    VALUES ('legacy-job', :artifact, '{"missingPlanningValues": ["material"], "diagnostics": []}'::jsonb,
                    'ready', '{"material": "PETG", "artifactFilename": "cube.gcode"}'::jsonb,
                    '{"priority": 7}'::jsonb)"""),
                {"artifact": f"sha256:{digest}"},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            material_columns = (
                connection.execute(
                    sa.text("""SELECT table_name FROM information_schema.columns
                    WHERE table_schema = current_schema() AND column_name = 'material'
                    AND data_type IN ('text', 'character varying', 'character')""")
                )
                .scalars()
                .all()
            )
            assert material_columns, (
                "legacy material must be backfilled into a typed material column"
            )
            metadata = sa.MetaData()
            values = []
            for name in material_columns:
                table = sa.Table(name, metadata, autoload_with=connection)
                values.extend(connection.scalars(sa.select(table.c.material)).all())
            assert "PETG" in values
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()


def test_migrated_persistence_schema_has_no_json_storage_columns(
    migrated_postgresql_schema: None,
) -> None:
    from backend.app.persistence import database

    with database.engine.connect() as connection:
        json_columns = connection.execute(
            sa.text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND data_type IN ('json', 'jsonb')
                ORDER BY table_name, column_name
                """
            )
        ).all()

    assert json_columns == []


def test_import_and_job_facts_are_persisted_without_generic_tree_relations(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b";TIME:3723\nG28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    assert imported.json()["extractedMetadata"]["estimatedDuration"] == 3723
    artifact_id = imported.json()["artifact"]["id"]
    created = client.post(
        f"/api/v1/import/{artifact_id}/jobs", json={"material": "PLA"}
    )
    assert created.status_code == 201
    job = created.json()
    assert job["executionData"]["material"] == "PLA"
    assert job["schedulingData"]["priority"] == 0
    assert job["state"] == "ready"

    jobs.import_service = jobs.ImportService()
    assert client.get(f"/api/v1/jobs/{job['id']}").json() == job
    assert client.get("/api/v1/queue").json() == {"jobs": [job]}

    with database.engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT state FROM job_history WHERE job_id = :job_id"),
                {"job_id": job["id"]},
            ).scalar_one()
            == "ready"
        )
        tree_tables = (
            connection.execute(
                sa.text(
                    """
                SELECT table_name FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND column_name IN ('field', 'path', 'kind')
                GROUP BY table_name
                HAVING count(DISTINCT column_name) = 3
                ORDER BY table_name
                """
                )
            )
            .scalars()
            .all()
        )

    assert tree_tables == [], (
        f"generic tree storage is not typed domain persistence: {tree_tables}"
    )


def test_created_job_priority_is_persisted_as_a_typed_integer_fact(
    client: TestClient,
) -> None:
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import", files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")}
    )
    artifact_id = imported.json()["artifact"]["id"]
    created = client.post(
        f"/api/v1/import/{artifact_id}/jobs", json={"material": "PLA"}
    )
    assert created.status_code == 201

    with database.engine.connect() as connection:
        priority_columns = connection.execute(
            sa.text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND column_name = 'priority'
                  AND data_type IN ('smallint', 'integer', 'bigint', 'numeric')
                """
            )
        ).all()
        assert priority_columns, "job priority must be stored as a typed integer column"
        metadata = sa.MetaData()
        values = []
        for table_name, column_name in priority_columns:
            table = sa.Table(table_name, metadata, autoload_with=connection)
            values.extend(connection.scalars(sa.select(table.c[column_name])).all())

    assert 0 in values

    with pytest.raises(sa.exc.IntegrityError), database.engine.begin() as connection:
        connection.execute(
            sa.text("UPDATE jobs SET priority = 1.5 WHERE id = :job_id"),
            {"job_id": created.json()["id"]},
        )


def test_migrated_schema_rejects_orphan_job_artifact_and_history_job_references(
    migrated_postgresql_schema: None, artifact_storage_path: Path
) -> None:
    artifact_storage_path.mkdir()
    (artifact_storage_path / "orphan.gcode").write_bytes(b"G28\n")

    from backend.app.persistence import database

    with pytest.raises(sa.exc.IntegrityError), database.engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO jobs (id, artifact_ref, state)
                VALUES ('orphan-artifact-job', 'missing-artifact', 'ready')
                """
            )
        )

    with pytest.raises(sa.exc.IntegrityError), database.engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO job_history (id, job_id, state)
                VALUES ('orphan-history', 'missing-job', 'ready')
                """
            )
        )
