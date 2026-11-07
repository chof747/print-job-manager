from fastapi.testclient import TestClient

from backend.app.api.v1 import jobs


def test_eligibility_request_requires_typed_printer_id(shell_client: TestClient) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    imported = shell_client.post(
        "/api/v1/import",
        files={"file": ("part.gcode", b"G28\n", "text/x.gcode")},
    )
    assert imported.status_code == 201
    created = shell_client.post(
        f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={"material": "PLA"}
    )
    assert created.status_code == 201

    malformed = shell_client.post(
        f"/api/v1/jobs/{created.json()['id']}/eligibility", json={"printer": {"id": 42}}
    )
    assert malformed.status_code == 422

    openapi = shell_client.get("/openapi.json").json()

    def resolve(schema: dict) -> dict:
        if "$ref" in schema:
            return openapi["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
        return schema

    request = openapi["paths"]["/api/v1/jobs/{job_id}/eligibility"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    request_schema = resolve(request)
    assert "printer" in request_schema["required"]
    printer = resolve(request_schema["properties"]["printer"])
    assert "id" in printer["required"]
    assert printer["properties"]["id"]["type"] == "string"
