from pathlib import Path

import pytest
import sqlalchemy as sa


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
                INSERT INTO jobs (
                    id, artifact_ref, parsed_metadata_snapshot, state,
                    execution_data, scheduling_data
                ) VALUES (
                    'orphan-artifact-job', 'missing-artifact', '{}'::jsonb, 'ready',
                    '{}'::jsonb, '{}'::jsonb
                )
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
