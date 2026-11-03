import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.api.v1 import jobs


def test_queue_can_be_sliced_by_material(shell_client: TestClient) -> None:
    jobs.import_service = jobs.ImportService(
        storage=jobs.InMemoryStorage(),
        repository=jobs.InMemoryImportRepository(),
        job_repository=jobs.InMemoryJobRepository(),
    )
    created = []
    for material in ("PLA", "PETG"):
        imported = shell_client.post(
            "/api/v1/import",
            files={"file": (f"{material}.gcode", f"; {material}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        response = shell_client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": material},
        )
        assert response.status_code == 201
        created.append(response.json())

    queue = shell_client.get("/api/v1/queue", params={"material": "PLA"})

    assert queue.status_code == 200
    assert [job["id"] for job in queue.json()["jobs"]] == [created[0]["id"]]


def test_queue_can_be_sliced_by_minimum_estimated_duration(client: TestClient) -> None:
    created = []
    for seconds in (600, 3600):
        imported = client.post(
            "/api/v1/import",
            files={
                "file": (f"{seconds}.gcode", f";TIME:{seconds}\nG28\n".encode(), "text/x.gcode")
            },
        )
        assert imported.status_code == 201
        response = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert response.status_code == 201
        created.append(response.json())

    queue = client.get("/api/v1/queue", params={"minDurationSeconds": 1800})

    assert queue.status_code == 200
    assert [job["id"] for job in queue.json()["jobs"]] == [created[1]["id"]]


def test_queue_can_be_sliced_by_minimum_priority(client: TestClient) -> None:
    created = []
    for priority in (0, 20):
        imported = client.post(
            "/api/v1/import",
            files={
                "file": (
                    f"priority-{priority}.gcode",
                    f"; priority {priority}\nG28\n".encode(),
                    "text/x.gcode",
                )
            },
        )
        assert imported.status_code == 201
        response = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert response.status_code == 201
        job = response.json()
        updated = client.patch(
            f"/api/v1/jobs/{job['id']}/scheduling",
            json={"priority": priority, "expectedVersion": job["version"]},
        )
        assert updated.status_code == 200
        created.append(updated.json())

    queue = client.get("/api/v1/queue", params={"minPriority": 10})

    assert queue.status_code == 200
    assert [job["id"] for job in queue.json()["jobs"]] == [created[1]["id"]]


def test_cockpit_distinguishes_active_failures_and_terminal_history(client: TestClient) -> None:
    from backend.app.persistence.database import SessionFactory

    job_ids = {}
    for state in ("ready", "failed", "completed", "cancelled", "archived"):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"{state}.gcode", f"; {state}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert created.status_code == 201
        job_ids[state] = created.json()["id"]

    # Execution lifecycle transitions are not exposed yet; seed their outcomes.
    with SessionFactory.begin() as session:
        for state, job_id in job_ids.items():
            session.execute(
                text("UPDATE jobs SET state = :state WHERE id = :job_id"),
                {"state": state, "job_id": job_id},
            )

    response = client.get("/api/v1/cockpit")

    assert response.status_code == 200
    cockpit = response.json()
    assert {job["id"] for job in cockpit["activeJobs"]} == {job_ids["ready"]}
    assert {job["id"] for job in cockpit["failures"]} == {job_ids["failed"]}
    assert {job["id"] for job in cockpit["recentHistory"]} == {
        job_ids[state] for state in ("failed", "completed", "cancelled", "archived")
    }


def test_cockpit_can_be_sliced_by_parser_diagnostic_code(client: TestClient) -> None:
    job_ids = []
    for filename, content in (
        ("malformed.gcode", b";TIME:not-a-duration\nG28\n"),
        ("clean.gcode", b";TIME:3600\nG28\n"),
    ):
        imported = client.post(
            "/api/v1/import", files={"file": (filename, content, "text/x.gcode")}
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    response = client.get("/api/v1/cockpit", params={"diagnosticCode": "malformed_metadata"})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_combines_material_duration_and_priority_filters(client: TestClient) -> None:
    job_ids = []
    for index, (material, duration, priority) in enumerate(
        (("PLA", 3600, 20), ("PETG", 3600, 20), ("PLA", 600, 20), ("PLA", 3600, 0))
    ):
        imported = client.post(
            "/api/v1/import",
            files={
                "file": (
                    f"job-{index}.gcode",
                    f";TIME:{duration}\n; job {index}\nG28\n".encode(),
                    "text/x.gcode",
                )
            },
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": material},
        )
        assert created.status_code == 201
        job = created.json()
        updated = client.patch(
            f"/api/v1/jobs/{job['id']}/scheduling",
            json={"expectedVersion": job["version"], "priority": priority},
        )
        assert updated.status_code == 200
        job_ids.append(job["id"])

    response = client.get(
        "/api/v1/cockpit",
        params={"material": "PLA", "minDurationSeconds": 1800, "minPriority": 10},
    )

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_combines_due_date_tag_and_assignment_filters(client: TestClient) -> None:
    job_ids = []
    cases = (
        ("2026-11-07", ["urgent"], "required"),
        ("2026-12-07", ["urgent"], "required"),
        ("2026-11-07", ["routine"], "required"),
        ("2026-11-07", ["urgent"], "preferred"),
    )
    for index, (due_date, tags, mode) in enumerate(cases):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", f"; {index}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert created.status_code == 201
        job = created.json()
        updated = client.patch(
            f"/api/v1/jobs/{job['id']}/scheduling",
            json={
                "expectedVersion": job["version"],
                "dueDate": due_date,
                "tags": tags,
                "printerAssignment": {"mode": mode, "printerId": "printer-1"},
            },
        )
        assert updated.status_code == 200
        job_ids.append(job["id"])

    response = client.get(
        "/api/v1/cockpit",
        params={"dueBefore": "2026-11-08", "tag": "urgent", "assignmentMode": "required"},
    )

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_combines_consumption_and_print_characteristic_filters(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cases = (
        (12.5, 0.4, 20.0, "PrusaSlicer"),
        (50.0, 0.4, 20.0, "PrusaSlicer"),
        (12.5, 0.6, 20.0, "PrusaSlicer"),
        (12.5, 0.4, 80.0, "PrusaSlicer"),
        (12.5, 0.4, 20.0, "OrcaSlicer"),
    )

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        weight, nozzle, dimension_x, slicer = cases[int(content.decode())]
        return {
            "extractedMetadata": {
                "material": "PLA", "filamentWeightGrams": weight,
                "nozzleDiameter": nozzle,
                "dimensions": {"x": dimension_x, "y": 30.0, "z": 40.0},
                "slicer": slicer,
            },
            "missingPlanningValues": [], "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    job_ids = []
    for index in range(len(cases)):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", str(index).encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={})
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    response = client.get(
        "/api/v1/cockpit",
        params={
            "maxFilamentWeightGrams": 20, "nozzleDiameter": 0.4,
            "maxDimensionX": 40, "slicer": "PrusaSlicer",
        },
    )

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_can_be_sliced_by_metadata_provenance_parser(client: TestClient) -> None:
    job_ids = []
    for filename, content in (
        ("prusa.gcode", b"; filament_type = PLA\nG28\n"),
        ("cura.gcode", b";TIME:3600\nG28\n"),
    ):
        imported = client.post(
            "/api/v1/import", files={"file": (filename, content, "text/x.gcode")}
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    response = client.get("/api/v1/cockpit", params={"provenanceParser": "prusa-family"})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_can_find_jobs_unassigned_to_a_printer(client: TestClient) -> None:
    job_ids = []
    for index in range(2):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", f"; {index}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs",
            json={"material": "PLA"},
        )
        assert created.status_code == 201
        job_ids.append(created.json()["id"])
        if index == 1:
            updated = client.patch(
                f"/api/v1/jobs/{job_ids[-1]}/scheduling",
                json={
                    "expectedVersion": created.json()["version"],
                    "printerAssignment": {"mode": "required", "printerId": "printer-1"},
                },
            )
            assert updated.status_code == 200

    response = client.get("/api/v1/cockpit", params={"assignmentMode": "unassigned"})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_nozzle_filter_includes_user_supplied_requirement(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {
            "extractedMetadata": {"material": "PLA"},
            "missingPlanningValues": ["nozzleDiameter"],
            "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    job_ids = []
    for index, nozzle in enumerate((0.4, 0.6)):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", f"; {index}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['import']['id']}/jobs",
            json={"nozzleDiameter": nozzle},
        )
        assert created.status_code == 201
        assert created.json()["executionData"]["nozzleDiameter"] == nozzle
        job_ids.append(created.json()["id"])

    response = client.get("/api/v1/cockpit", params={"nozzleDiameter": 0.4})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_cockpit_nozzle_filter_includes_job_without_extracted_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        return {"missingPlanningValues": ["material", "nozzleDiameter"], "diagnostics": []}

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    imported = client.post(
        "/api/v1/import", files={"file": ("manual.gcode", b"G28\n", "text/x.gcode")}
    )
    assert imported.status_code == 201
    created = client.post(
        f"/api/v1/import/{imported.json()['import']['id']}/jobs",
        json={"material": "PLA", "nozzleDiameter": 0.4},
    )
    assert created.status_code == 201

    response = client.get("/api/v1/cockpit", params={"nozzleDiameter": 0.4})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [created.json()["id"]]


def test_cockpit_can_slice_by_y_and_z_dimensions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    dimensions = ((20.0, 30.0), (80.0, 30.0), (20.0, 90.0))

    def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
        y, z = dimensions[int(content.decode())]
        return {
            "extractedMetadata": {"material": "PLA", "dimensions": {"x": 10.0, "y": y, "z": z}},
            "missingPlanningValues": [], "diagnostics": [],
        }

    monkeypatch.setattr(jobs.GcodeParser, "parse", parse)
    job_ids = []
    for index in range(len(dimensions)):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", str(index).encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(f"/api/v1/import/{imported.json()['import']['id']}/jobs", json={})
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    response = client.get("/api/v1/cockpit", params={"maxDimensionY": 40, "maxDimensionZ": 50})

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["activeJobs"]] == [job_ids[0]]


def test_recent_history_orders_by_terminal_event_not_job_creation(client: TestClient) -> None:
    from backend.app.persistence.database import SessionFactory

    job_ids = []
    for index in range(2):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", f"; {index}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={"material": "PLA"}
        )
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    # No public lifecycle transition API exists yet; seed terminal event timestamps.
    with SessionFactory.begin() as session:
        for job_id, timestamp in zip(job_ids, ("2026-11-01T12:00:00Z", "2026-11-02T12:00:00Z")):
            session.execute(text("UPDATE jobs SET state = 'completed' WHERE id = :id"), {"id": job_id})
            session.execute(
                text("INSERT INTO job_history (id, job_id, state, created_at) "
                     "VALUES (:event_id, :job_id, 'completed', CAST(:timestamp AS timestamptz))"),
                {"event_id": f"{job_id}-completed", "job_id": job_id, "timestamp": timestamp},
            )

    response = client.get("/api/v1/cockpit")

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["recentHistory"]] == job_ids[::-1]


def test_recent_history_is_limited_to_the_20_newest_terminal_jobs(client: TestClient) -> None:
    from backend.app.persistence.database import SessionFactory

    job_ids = []
    for index in range(21):
        imported = client.post(
            "/api/v1/import",
            files={"file": (f"job-{index}.gcode", f"; {index}\nG28\n".encode(), "text/x.gcode")},
        )
        assert imported.status_code == 201
        created = client.post(
            f"/api/v1/import/{imported.json()['artifact']['id']}/jobs", json={"material": "PLA"}
        )
        assert created.status_code == 201
        job_ids.append(created.json()["id"])

    # Seed terminal events because lifecycle transitions are not yet public.
    with SessionFactory.begin() as session:
        for index, job_id in enumerate(job_ids):
            session.execute(text("UPDATE jobs SET state = 'completed' WHERE id = :id"), {"id": job_id})
            session.execute(
                text("INSERT INTO job_history (id, job_id, state, created_at) "
                     "VALUES (:event_id, :job_id, 'completed', "
                     "CAST('2026-11-01T00:00:00Z' AS timestamptz) + :seconds * INTERVAL '1 second')"),
                {"event_id": f"{job_id}-completed", "job_id": job_id, "seconds": index},
            )

    response = client.get("/api/v1/cockpit")

    assert response.status_code == 200
    assert [job["id"] for job in response.json()["recentHistory"]] == job_ids[:0:-1]


def test_cockpit_openapi_describes_projection_for_api_clients(shell_client: TestClient) -> None:
    openapi = shell_client.get("/openapi.json").json()
    schemas = openapi["components"]["schemas"]

    def resolve(schema: dict) -> dict:
        return schemas[schema["$ref"].rsplit("/", 1)[-1]] if "$ref" in schema else schema

    response = openapi["paths"]["/api/v1/cockpit"]["get"]["responses"]["200"]
    projection = resolve(response["content"]["application/json"]["schema"])
    assert {"activeJobs", "failures", "recentHistory"} <= set(projection.get("required", []))
    for field in ("activeJobs", "failures", "recentHistory"):
        collection = projection["properties"][field]
        assert collection["type"] == "array"
        job = resolve(collection["items"])
        assert {"id", "state", "executionData", "schedulingData"} <= set(job.get("properties", {}))


def test_cockpit_openapi_describes_active_job_planning_fields(shell_client: TestClient) -> None:
    openapi = shell_client.get("/openapi.json").json()
    schemas = openapi["components"]["schemas"]

    def resolve(schema: dict) -> dict:
        return schemas[schema["$ref"].rsplit("/", 1)[-1]] if "$ref" in schema else schema

    response = openapi["paths"]["/api/v1/cockpit"]["get"]["responses"]["200"]
    projection = resolve(response["content"]["application/json"]["schema"])
    job = resolve(projection["properties"]["activeJobs"]["items"])
    execution = resolve(job["properties"]["executionData"])
    scheduling = resolve(job["properties"]["schedulingData"])

    assert {"material", "artifactFilename", "nozzleDiameter"} <= set(execution.get("properties", {}))
    assert {"priority", "dueDate", "printerAssignment"} <= set(scheduling.get("properties", {}))
