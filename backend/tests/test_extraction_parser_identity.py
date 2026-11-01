import pytest
from fastapi.testclient import TestClient


def test_extraction_records_the_parser_identity_used_for_its_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.app.api.v1 import jobs

    class AlternateParser(jobs.GcodeParser):
        parser_id = "alternate-gcode-parser"
        parser_version = "2"

    monkeypatch.setattr(jobs, "GcodeParser", AlternateParser)
    jobs.import_service = jobs.ImportService()
    imported = client.post(
        "/api/v1/import",
        files={"file": ("cube.gcode", b"; filament_type = PLA\nG28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201

    record = jobs.SqlAlchemyImportRepository().load_import(imported.json()["import"]["id"])
    assert record is not None
    assert record["extraction"]["parser"] == "alternate-gcode-parser"
    assert record["extraction"]["parserVersion"] == "2"
    assert record["parsed"]["extractedMetadata"]["material"] == "PLA"
