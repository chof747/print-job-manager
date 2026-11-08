from fastapi.testclient import TestClient


def test_job_creation_openapi_describes_nozzle_diameter_requirement(
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
    nozzle = resolve(resolve(request)["properties"]["nozzleDiameter"])

    assert nozzle["type"] == "number"
