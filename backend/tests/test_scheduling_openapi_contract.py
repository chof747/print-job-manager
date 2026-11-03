from fastapi.testclient import TestClient


def test_scheduling_update_openapi_describes_returned_job_for_api_clients(
    shell_client: TestClient,
) -> None:
    openapi = shell_client.get("/openapi.json").json()
    schema = openapi["paths"]["/api/v1/jobs/{job_id}/scheduling"]["patch"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    if "$ref" in schema:
        schema = openapi["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]

    assert {"id", "version", "schedulingData"} <= set(schema.get("properties", {}))
