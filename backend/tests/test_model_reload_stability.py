import gc

from backend.app.persistence.models import JobRecord


def test_collected_models_remain_usable_after_schema_fixture_reload(
    migrated_postgresql_schema: None,
) -> None:
    # Pytest can retain model classes imported during collection across reloads.
    gc.collect()
    record = JobRecord(artifact_ref="artifact")
    assert record.artifact_ref == "artifact"
