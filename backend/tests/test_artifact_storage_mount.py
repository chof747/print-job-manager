from pathlib import Path

from backend.app.api.v1 import jobs


def test_import_keeps_coordination_files_inside_shared_artifact_mount(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "mount-parent"
    artifact_dir = parent / "artifacts"
    artifact_dir.mkdir(parents=True)
    storage = jobs.FileSystemStorage(artifact_dir)
    service = jobs.ImportService(
        storage=storage, repository=jobs.InMemoryImportRepository()
    )
    imported = service.import_gcode(
        filename="cube.gcode", media_type="text/x.gcode", content=b"G28\n"
    )
    assert storage.retrieve(imported["artifact"]["id"]) == b"G28\n"
    assert list(parent.iterdir()) == [artifact_dir]
