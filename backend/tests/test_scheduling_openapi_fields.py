from fastapi.testclient import TestClient


def test_scheduling_response_describes_mutable_fields_to_generated_clients(
    shell_client: TestClient,
) -> None:
    openapi = shell_client.get("/openapi.json").json()
    schema = openapi["paths"]["/api/v1/jobs/{job_id}/scheduling"]["patch"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]

    def resolve(value: dict) -> dict:
        if "$ref" in value:
            return openapi["components"]["schemas"][value["$ref"].rsplit("/", 1)[-1]]
        return value

    scheduling = resolve(resolve(schema)["properties"]["schedulingData"])
    assert {"priority", "dueDate", "notes", "tags", "printerAssignment"} <= set(
        scheduling.get("properties", {})
    )
