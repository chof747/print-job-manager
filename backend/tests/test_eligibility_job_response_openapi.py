from fastapi.testclient import TestClient


def test_job_response_openapi_describes_typed_hard_requirements(shell_client: TestClient) -> None:
    openapi = shell_client.get("/openapi.json").json()

    def resolve(schema: dict) -> dict:
        if "$ref" in schema:
            return resolve(openapi["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]])
        if "anyOf" in schema:
            return resolve(next(item for item in schema["anyOf"] if item.get("type") != "null"))
        return schema

    response = openapi["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    job = resolve(response)
    execution = resolve(job["properties"]["executionData"])
    requirements = resolve(execution["properties"]["requirements"])["properties"]

    assert resolve(requirements["enclosure"])["type"] == "boolean"
    assert resolve(requirements["hardenedNozzle"])["type"] == "boolean"
    material = resolve(requirements["material"])["properties"]
    assert resolve(material["color"])["type"] == "string"
    assert resolve(material["amountGrams"])["type"] == "number"
    volume = resolve(requirements["buildVolume"])["properties"]
    assert all(resolve(volume[axis])["type"] == "number" for axis in ("x", "y", "z"))
