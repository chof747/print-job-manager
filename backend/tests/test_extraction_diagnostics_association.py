from itertools import permutations

import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_conflicting_and_malformed_diagnostics_belong_to_the_extraction(
    client: TestClient,
) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={
            "file": (
                "cube.gcode",
                b"; filament_type = PLA\n; filament_type = PETG\n;TIME:bad\nG28\n",
                "text/x.gcode",
            )
        },
    )
    assert imported.status_code == 201
    artifact_id = imported.json()["artifact"]["id"]
    record = jobs.SqlAlchemyImportRepository().load_import(artifact_id)
    assert record is not None
    extraction_id = record["extraction"]["id"]

    jobs.import_service = jobs.ImportService()
    review = client.get(f"/api/v1/import/{artifact_id}")
    assert review.status_code == 200
    expected = {
        ("conflicting_metadata", "filament_type"),
        ("malformed_metadata", "TIME"),
    }
    assert {(d["code"], d["sourceKey"]) for d in review.json()["diagnostics"]} == expected

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        metadata.reflect(bind=connection)
        extraction = metadata.tables["artifact_extractions"]
        found = set()
        for table in metadata.tables.values():
            links = [
                column for column in table.columns
                if any(fk.column is extraction.c.id for fk in column.foreign_keys)
            ]
            text_columns = [c for c in table.columns if isinstance(c.type, sa.String)]
            for link in links:
                for code, source in permutations(text_columns, 2):
                    for code_value, source_value in expected:
                        if connection.execute(
                            sa.select(sa.literal(True)).where(
                                link == extraction_id,
                                code == code_value,
                                source == source_value,
                            )
                        ).first() is not None:
                            found.add((code_value, source_value))

    assert found == expected, "diagnostic records must reference their extraction"
