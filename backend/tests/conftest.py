import importlib
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.api.v1 import jobs


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def package_json(repo_root: Path) -> dict:
    import json

    return json.loads((repo_root / "package.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(migrated_postgresql_schema: None) -> Iterator[TestClient]:
    # Each import-flow test starts with an empty, migrated PostgreSQL schema.
    jobs.import_service = jobs.ImportService()
    from backend.app import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def shell_client() -> Iterator[TestClient]:
    from backend.app import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def artifact_storage_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    storage_path = tmp_path / "artifacts"
    monkeypatch.setenv("PRINT_JOB_MANAGER_ARTIFACT_STORAGE_PATH", str(storage_path))

    from backend.app import config as app_config

    app_config.get_settings.cache_clear()
    importlib.reload(jobs)
    try:
        yield storage_path
    finally:
        shutil.rmtree(storage_path, ignore_errors=True)
        app_config.get_settings.cache_clear()


@pytest.fixture
def migrated_postgresql_schema(
    artifact_storage_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
) -> Iterator[None]:
    del artifact_storage_path
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
    original_database_url = os.environ.get("PRINT_JOB_MANAGER_DATABASE_URL")
    monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", scoped_database_url)

    from backend.app import config as app_config
    from backend.app import main
    from backend.app.api import v1
    from backend.app.persistence import database, job_repository, models

    app_config.get_settings.cache_clear()
    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(job_repository)
    importlib.reload(jobs)
    importlib.reload(v1)
    importlib.reload(main)

    alembic_config = Config(str(repo_root / "backend" / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(repo_root / "backend" / "alembic")
    )
    alembic_config.set_main_option("sqlalchemy.url", scoped_database_url)
    try:
        command.upgrade(alembic_config, "head")
        yield
    finally:
        database.engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()
        if original_database_url is None:
            monkeypatch.delenv("PRINT_JOB_MANAGER_DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("PRINT_JOB_MANAGER_DATABASE_URL", original_database_url)
        app_config.get_settings.cache_clear()
        importlib.reload(database)
        importlib.reload(models)
        importlib.reload(job_repository)
        importlib.reload(jobs)
        importlib.reload(v1)
        importlib.reload(main)
