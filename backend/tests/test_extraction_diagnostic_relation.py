import sqlalchemy as sa
from fastapi.testclient import TestClient


def test_malformed_metadata_diagnostic_is_persisted_as_a_relation(
    client: TestClient,
) -> None:
    from backend.app.persistence import database

    response = client.post(
        "/api/v1/import",
        files={"file": ("bad.gcode", b";TIME:not-a-duration\nG28\n", "text/x.gcode")},
    )
    assert response.status_code == 201
    assert {"code": "malformed_metadata", "sourceKey": "TIME"} in response.json()[
        "diagnostics"
    ]

    # A diagnostic must be queryable in ordinary relational columns, not just
    # embedded in the parser's JSON snapshot.
    with database.engine.connect() as connection:
        inspector = sa.inspect(connection)
        found = False
        for table_name in inspector.get_table_names():
            table = sa.Table(table_name, sa.MetaData(), autoload_with=connection)
            text_columns = [
                column for column in table.columns if isinstance(column.type, sa.String)
            ]
            for code_column in text_columns:
                for source_column in text_columns:
                    if code_column is source_column:
                        continue
                    query = sa.select(sa.literal(1)).select_from(table).where(
                        code_column == "malformed_metadata", source_column == "TIME"
                    )
                    if connection.execute(query).first() is not None:
                        found = True
        assert found, "malformed diagnostic code and source key must be relational facts"
