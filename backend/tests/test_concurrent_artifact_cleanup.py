from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest

from backend.app.api.v1 import jobs


def test_failed_concurrent_import_does_not_delete_successful_artifact(
    tmp_path: Path,
) -> None:
    both_checked = Barrier(2, timeout=5)
    successful_import_finished = Event()

    class SynchronizedStorage(jobs.FileSystemStorage):
        def store(self, *, filename: str, media_type: str, content: bytes) -> str:
            both_checked.wait()
            return super().store(
                filename=filename, media_type=media_type, content=content
            )

    class SuccessfulParser:
        def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
            return {"missingPlanningValues": ["material"], "diagnostics": []}

    class FailingParser:
        def parse(self, *, artifact_id: str, content: bytes) -> dict[str, object]:
            if not successful_import_finished.wait(timeout=5):
                raise TimeoutError("successful import did not finish")
            raise ValueError("parser failed")

    storage = SynchronizedStorage(tmp_path / "artifacts")
    repository = jobs.InMemoryImportRepository()
    success = jobs.ImportService(
        storage=storage, parser=SuccessfulParser(), repository=repository
    )
    failure = jobs.ImportService(
        storage=storage, parser=FailingParser(), repository=repository
    )
    args = {"filename": "cube.gcode", "media_type": "text/x.gcode", "content": b"G28\n"}

    with ThreadPoolExecutor(max_workers=2) as pool:
        successful = pool.submit(success.import_gcode, **args)
        failing = pool.submit(failure.import_gcode, **args)
        try:
            imported = successful.result(timeout=5)
        finally:
            successful_import_finished.set()
        with pytest.raises(ValueError, match="parser failed"):
            failing.result(timeout=5)

    assert storage.retrieve(imported["artifact"]["id"]) == b"G28\n"
