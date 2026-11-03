from fastapi.testclient import TestClient


def test_scheduling_openapi_does_not_allow_null_tags(shell_client: TestClient) -> None:
    openapi = shell_client.get("/openapi.json").json()
    request_schema = openapi["paths"]["/api/v1/jobs/{job_id}/scheduling"]["patch"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    request = openapi["components"]["schemas"][request_schema["$ref"].rsplit("/", 1)[-1]]
    tags = request["properties"]["tags"]

    assert "tags" not in request.get("required", [])
    assert tags.get("type") != "null"
    assert all(option.get("type") != "null" for option in tags.get("anyOf", []))
