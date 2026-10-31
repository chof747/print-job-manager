from itertools import permutations

import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_material_provenance_is_linked_to_its_extraction_and_reviewed(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={
            "file": (
                "cube.gcode",
                b"; filament_type = PLA\nG28\n",
                "text/x.gcode",
            )
        },
    )
    assert response.status_code == 201
    artifact_id = response.json()["artifact"]["id"]
    imported = jobs.SqlAlchemyImportRepository().load_import(artifact_id)
    assert imported is not None
    extraction_id = imported["extraction"]["id"]

    jobs.import_service = jobs.ImportService()
    review = client.get(f"/api/v1/import/{artifact_id}")
    assert review.status_code == 200
    assert review.json()["provenance"]["material"] == {
        "parser": "prusa-family",
        "sourceKey": "filament_type",
    }

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
            text_columns = [c for c in table.columns if isinstance(c.type, sa.String)]
            for link in links:
                for field, parser, source in permutations(text_columns, 3):
                    found |= connection.execute(
                        sa.select(sa.literal(True)).where(
                            link == extraction_id,
                            field == "material",
                            parser == "prusa-family",
                            source == "filament_type",
                        )
                    ).first() is not None

    assert found, "material provenance must be a field-specific extraction relation"
