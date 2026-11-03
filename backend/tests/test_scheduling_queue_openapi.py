from fastapi.testclient import TestClient


def test_queue_openapi_describes_job_versions_and_scheduling_for_clients(
    shell_client: TestClient,
) -> None:
    openapi = shell_client.get("/openapi.json").json()
    schema = openapi["paths"]["/api/v1/queue"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    def resolve(value: dict) -> dict:
        if "$ref" in value:
            return openapi["components"]["schemas"][value["$ref"].rsplit("/", 1)[-1]]
        return value

    queue_properties = resolve(schema).get("properties", {})
    assert "jobs" in queue_properties
    job = resolve(queue_properties["jobs"]["items"])
    assert {"id", "version", "schedulingData"} <= set(job.get("properties", {}))
