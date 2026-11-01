import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_backfill_preserves_valid_large_legacy_duration(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1.jobs import GcodeParser
    from backend.app.config import get_settings

    database_url = os.environ.get("PRINT_JOB_MANAGER_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip(
            "PRINT_JOB_MANAGER_TEST_DATABASE_URL must name a disposable PostgreSQL database"
        )

    duration = 2**63
    parsed = GcodeParser().parse(
        artifact_id="unused", content=f";TIME:{duration}\nG28\n".encode()
    )
    assert parsed["extractedMetadata"]["estimatedDuration"] == duration

    schema = f"test_duration_{uuid4().hex}"
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
    digest = "c" * 64
    try:
        command.upgrade(config, "20260925_0002")
        with engine.begin() as connection:
            connection.execute(
                sa.text("""INSERT INTO artifacts
                    (id, sha256, storage_key, filename, parsed_metadata_snapshot)
                    VALUES (:id, :digest, :id, 'cube.gcode', CAST(:parsed AS jsonb))"""),
                {
                    "id": f"sha256:{digest}",
                    "digest": digest,
                    "parsed": json.dumps(parsed),
                },
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT estimated_duration FROM artifacts")
                ).scalar_one()
                == duration
            )
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        get_settings.cache_clear()
