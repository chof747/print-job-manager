import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_imported_duration_is_stored_as_a_typed_relational_fact(
    client: TestClient,
) -> None:
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b";TIME:3723\nG28\n", "text/x.gcode")},
    )
    assert response.status_code == 201
    assert response.json()["extractedMetadata"]["estimatedDuration"] == 3723

    with database.engine.connect() as connection:
        columns = connection.execute(
            sa.text(
                """SELECT table_name, column_name FROM information_schema.columns
                   WHERE table_schema = current_schema()
                     AND column_name ILIKE '%duration%'
                     AND data_type IN ('smallint', 'integer', 'bigint', 'numeric',
                                       'real', 'double precision')"""
            )
        ).all()
        assert columns, "estimated duration must be stored in a typed numeric column"
        metadata = sa.MetaData()
        values = []
        for table_name, column_name in columns:
            table = sa.Table(table_name, metadata, autoload_with=connection)
            values.extend(connection.scalars(sa.select(table.c[column_name])).all())
        assert 3723 in values
