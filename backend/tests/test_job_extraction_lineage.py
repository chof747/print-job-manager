import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_job_records_which_extraction_created_it(client: TestClient) -> None:
    from backend.app.api.v1 import jobs
    from backend.app.persistence import database

    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"; filament_type = PLA\nG28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    import_id = imported.json()["import"]["id"]
    record = jobs.SqlAlchemyImportRepository().load_import(import_id)
    assert record is not None
    extraction_id = record["extraction"]["id"]
    jobs.import_service = jobs.ImportService()
    created = client.post(f"/api/v1/import/{import_id}/jobs", json={})
    assert created.status_code == 201
    job_id = created.json()["id"]

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        metadata.reflect(bind=connection)
        job_table = metadata.tables["jobs"]
        extraction = metadata.tables["artifact_extractions"]
        imports = metadata.tables["artifact_imports"]
        linked = False
        for column in job_table.columns:
            for foreign_key in column.foreign_keys:
                if foreign_key.column is extraction.c.id:
                    linked |= connection.execute(
                        sa.select(sa.literal(True)).where(
                            job_table.c.id == job_id, column == extraction_id
                        )
                    ).first() is not None
                elif foreign_key.column is imports.c.id:
                    linked |= connection.execute(
                        sa.select(sa.literal(True)).select_from(
                            job_table.join(imports, column == imports.c.id)
                        ).where(
                            job_table.c.id == job_id, imports.c.extraction_id == extraction_id
                        )
                    ).first() is not None

    assert linked, "job must reference the extraction used to create it"
