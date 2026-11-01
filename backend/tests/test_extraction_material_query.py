import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_material_and_weight_are_queryable_by_extraction(client: TestClient) -> None:
    from backend.app.api.v1.jobs import SqlAlchemyImportRepository
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={
            "file": (
                "cube.gcode",
                b"; filament_type = PLA\n; total filament used [g] = 12.5\nG28\n",
                "text/x.gcode",
            )
        },
    )
    assert response.status_code == 201
    assert response.json()["extractedMetadata"] == {
        "material": "PLA",
        "filamentWeightGrams": 12.5,
    }
    artifact_id = response.json()["artifact"]["id"]
    imported = SqlAlchemyImportRepository().load_import(artifact_id)
    assert imported is not None
    extraction_id = imported["extraction"]["id"]

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        metadata.reflect(bind=connection)
        extraction = metadata.tables["artifact_extractions"]
        found_material = False
        found_weight = False
        for table in metadata.tables.values():
            links = [
                column
                for column in table.columns
                if table is extraction and column is extraction.c.id
                or any(fk.column is extraction.c.id for fk in column.foreign_keys)
            ]
            for link in links:
                for column in table.columns:
                    if isinstance(column.type, sa.String):
                        found_material |= connection.execute(
                            sa.select(sa.literal(True)).where(
                                link == extraction_id, column == "PLA"
                            )
                        ).first() is not None
                    if isinstance(column.type, (sa.Numeric, sa.Float)):
                        found_weight |= connection.execute(
                            sa.select(sa.literal(True)).where(
                                link == extraction_id, column == 12.5
                            )
                        ).first() is not None

    assert found_material, "material must be a queryable fact linked to its extraction"
    assert found_weight, "filament weight must be a numeric fact linked to its extraction"
