from fastapi.testclient import TestClient


def test_eligibility_openapi_describes_typed_success_and_failure_explanations(
    shell_client: TestClient,
) -> None:
    openapi = shell_client.get("/openapi.json").json()

    def resolve(schema: dict) -> dict:
        if "$ref" in schema:
            return openapi["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
        return schema

    response = openapi["paths"]["/api/v1/jobs/{job_id}/eligibility"]["post"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    result = resolve(response)
    properties = result["properties"]

    assert {"eligible", "blocked", "failures"} <= set(result["required"])
    assert properties["eligible"]["type"] == "boolean"
    assert properties["blocked"]["type"] == "boolean"
    assert properties["failures"]["type"] == "array"
    failure = resolve(properties["failures"]["items"])
    assert "code" in failure["required"]
    assert failure["properties"]["code"]["type"] == "string"
