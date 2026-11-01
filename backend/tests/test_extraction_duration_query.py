import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_duration_is_queryable_by_extraction_as_a_numeric_fact(
    client: TestClient,
) -> None:
    from backend.app.api.v1.jobs import SqlAlchemyImportRepository
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b";TIME:3723\nG28\n", "text/x.gcode")},
    )
    assert response.status_code == 201
    assert response.json()["extractedMetadata"]["estimatedDuration"] == 3723
    imported = SqlAlchemyImportRepository().load_import(response.json()["artifact"]["id"])
    assert imported is not None
    extraction_id = imported["extraction"]["id"]

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        metadata.reflect(bind=connection)
        extraction = metadata.tables["artifact_extractions"]
        found = False
        for table in metadata.tables.values():
            links = [
                column
                for column in table.columns
                if (table is extraction and column is extraction.c.id)
                or any(fk.column is extraction.c.id for fk in column.foreign_keys)
            ]
            for link in links:
                for column in table.columns:
                    if isinstance(column.type, (sa.Integer, sa.Numeric, sa.Float)):
                        found |= connection.execute(
                            sa.select(sa.literal(True)).where(
                                link == extraction_id, column == 3723
                            )
                        ).first() is not None

    assert found, "duration must be a numeric fact linked to its extraction"
