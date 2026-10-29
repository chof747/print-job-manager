from fastapi.testclient import TestClient


def test_reupload_does_not_replace_original_artifact_import_facts(
    client: TestClient, monkeypatch
) -> None:
    from backend.app.api.v1 import jobs

    parses = iter(("PLA", "PETG"))

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": next(parses)},
            "missingPlanningValues": [],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    first = client.post(
        "/api/v1/import", files={"file": ("original.gcode", b"G28\n", "text/x.gcode")}
    )
    second = client.post(
        "/api/v1/import", files={"file": ("renamed.gcode", b"G28\n", "text/x.gcode")}
    )
    assert first.status_code == second.status_code == 201
    artifact_id = first.json()["artifact"]["id"]
    assert second.json()["artifact"]["id"] == artifact_id

    jobs.import_service = jobs.ImportService()
    created = client.post(f"/api/v1/import/{artifact_id}/jobs", json={})
    assert created.status_code == 201
    assert created.json()["executionData"] == {
        "artifactRef": artifact_id,
        "artifactFilename": "original.gcode",
        "material": "PLA",
        "extractedMetadata": {"material": "PLA"},
    }
    assert (
        second.json()["artifact"]["filename"]
        == created.json()["executionData"]["artifactFilename"]
    )
    assert (
        second.json()["extractedMetadata"]
        == created.json()["executionData"]["extractedMetadata"]
    )
    assert (
        second.json()["missingPlanningValues"] == first.json()["missingPlanningValues"]
    )
    assert second.json()["diagnostics"] == first.json()["diagnostics"]
