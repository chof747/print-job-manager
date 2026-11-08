from fastapi.testclient import TestClient


def test_job_creation_openapi_describes_typed_hard_enclosure_requirement(
    shell_client: TestClient,
) -> None:
    openapi = shell_client.get("/openapi.json").json()

    def resolve(schema: dict) -> dict:
        if "$ref" in schema:
            return openapi["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
        if "anyOf" in schema:
            return resolve(next(item for item in schema["anyOf"] if item.get("type") != "null"))
        return schema

    request = openapi["paths"]["/api/v1/import/{artifact_id}/jobs"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    requirements = resolve(resolve(request)["properties"]["requirements"])

    assert resolve(requirements["properties"]["enclosure"])["type"] == "boolean"
