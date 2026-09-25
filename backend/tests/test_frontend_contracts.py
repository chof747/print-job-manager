from pathlib import Path


def test_frontend_runtime_config_file_exists_with_api_base_url(repo_root: Path) -> None:
    import json

    runtime_config_path = repo_root / "frontend" / "public" / "runtime-config.json"

    assert runtime_config_path.is_file()

    runtime_config = json.loads(runtime_config_path.read_text(encoding="utf-8"))

    assert runtime_config["apiBaseUrl"]


def test_frontend_dev_server_smoke_tests_have_been_removed_from_committed_tests(
    repo_root: Path,
) -> None:
    frontend_root_tests = sorted(
        (repo_root / "backend" / "tests").glob("test_root_frontend*.py")
    )

    invalid_files = []
    for test_file in frontend_root_tests:
        if test_file.name == Path(__file__).name:
            continue

        source = test_file.read_text(encoding="utf-8")
        if "import subprocess" in source or "subprocess." in source:
            invalid_files.append(test_file.relative_to(repo_root).as_posix())

    assert invalid_files == [], (
        "frontend dev-server startup verification belongs in manual QA, not committed tests"
    )
