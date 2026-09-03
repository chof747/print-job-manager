from typing import Any, cast

import pytest

from backend.app.api.v1 import jobs


def test_ready_job_creation_persists_job_and_creation_history_atomically() -> None:
    class AtomicJobRepository:
        def __init__(self) -> None:
            self.jobs: list[dict[str, object]] = []
            self.history: list[dict[str, object]] = []
            self.fail = False

        def create_ready_job(
            self, *, job: dict[str, object], creation_history: dict[str, object]
        ) -> tuple[dict[str, object], bool]:
            if self.fail:
                raise RuntimeError("simulated persistence failure")
            self.jobs.append(job)
            self.history.append(creation_history)
            return job, True

        def active_queue(self) -> dict[str, list[object]]:
            queued_jobs: list[object] = list(self.jobs)
            return {"jobs": queued_jobs}

        def get_job(self, job_id: str) -> dict[str, object] | None:
            return next((job for job in self.jobs if job["id"] == job_id), None)

    repository = AtomicJobRepository()
    service = jobs.ImportService(
        repository=jobs.InMemoryImportRepository(), job_repository=repository
    )
    first_import = cast(
        dict[str, Any],
        service.import_gcode(
            filename="first-part.gcode", media_type="text/x.gcode", content=b"G28\n"
        ),
    )
    second_import = cast(
        dict[str, Any],
        service.import_gcode(
            filename="second-part.gcode", media_type="text/x.gcode", content=b"G1 X10\n"
        ),
    )

    first_job = cast(
        dict[str, Any],
        service.create_job(artifact_id=first_import["artifact"]["id"], material="PLA"),
    )

    assert repository.jobs == [first_job]
    assert repository.history == [{"jobId": first_job["id"], "state": "ready"}]
    assert first_job["executionData"]["artifactRef"] == first_import["artifact"]["id"]

    repository.fail = True
    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        service.create_job(artifact_id=second_import["artifact"]["id"], material="PETG")

    assert repository.jobs == [first_job]
    assert repository.history == [{"jobId": first_job["id"], "state": "ready"}]
