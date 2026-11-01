import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_missing_material_is_linked_to_extraction_and_fresh_review(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]
    record = jobs.SqlAlchemyImportRepository().load_import(artifact_id)
    assert record is not None
    extraction_id = record["extraction"]["id"]

    jobs.import_service = jobs.ImportService()
    review = client.get(f"/api/v1/import/{artifact_id}")
    assert review.status_code == 200
    assert review.json()["missingPlanningValues"] == ["material"]

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        metadata.reflect(bind=connection)
        extraction = metadata.tables["artifact_extractions"]
        found = False
        for table in metadata.tables.values():
            links = [
                column for column in table.columns
                if any(fk.column is extraction.c.id for fk in column.foreign_keys)
            ]
            for link in links:
                for column in table.columns:
                    if isinstance(column.type, sa.String):
                        found |= connection.execute(
                            sa.select(sa.literal(True)).where(
                                link == extraction_id, column == "material"
                            )
                        ).first() is not None

    assert found, "missing material must be a record linked to its extraction"
