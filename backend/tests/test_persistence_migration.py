import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_initial_migration_creates_artifact_job_and_history_schema(
    repo_root: Path, monkeypatch
) -> None:
    migration_path = (
        repo_root / "backend" / "alembic" / "versions" / "20260902_0001_create_jobs.py"
    )
    spec = importlib.util.spec_from_file_location(
        "initial_jobs_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    tables: dict[str, set[str]] = {}

    def create_table(name: str, *columns: sa.Column[object], **_: object) -> None:
        tables[name] = {
            column.name for column in columns if isinstance(column, sa.Column)
        }

    monkeypatch.setattr(migration.op, "create_table", create_table)
    monkeypatch.setattr(migration.op, "create_index", lambda *_args, **_kwargs: None)

    migration.upgrade()

    assert tables.keys() >= {"artifacts", "jobs", "job_history"}
    assert tables["artifacts"] >= {"id", "sha256", "storage_key"}
    assert tables["jobs"] >= {
        "id",
        "artifact_ref",
        "parsed_metadata_snapshot",
        "state",
    }
    assert tables["job_history"] >= {"id", "job_id", "state", "created_at"}


def test_artifact_filename_migration_adds_an_optional_filename_column(
    repo_root: Path, monkeypatch
) -> None:
    migration_path = (
        repo_root / "backend" / "alembic" / "versions" / "20260925_0002_add_artifact_filename.py"
    )
    spec = importlib.util.spec_from_file_location("artifact_filename_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    added_columns: list[tuple[str, sa.Column[object]]] = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added_columns.append((table, column)),
    )

    migration.upgrade()

    assert [(table, column.name, column.nullable) for table, column in added_columns] == [
        ("artifacts", "filename", True)
    ]
