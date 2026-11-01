import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_missing_material_is_persisted_as_a_relational_record(
    client: TestClient,
) -> None:
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"G28\n", "text/x.gcode")},
    )
    assert response.status_code == 201
    assert "material" in response.json()["missingPlanningValues"]

    with database.engine.connect() as connection:
        metadata = sa.MetaData()
        found = False
        for table_name in sa.inspect(connection).get_table_names():
            table = sa.Table(table_name, metadata, autoload_with=connection)
            for column in table.columns:
                if isinstance(column.type, sa.String):
                    query = sa.select(sa.literal(1)).select_from(table).where(
                        column == "material"
                    )
                    if connection.execute(query).first() is not None:
                        found = True
        assert found, "missing material must be stored as an individual relational record"
