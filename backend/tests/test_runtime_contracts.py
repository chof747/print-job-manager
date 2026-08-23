from pathlib import Path
import re
import subprocess
import tomllib


def test_backend_pyproject_declares_runtime_and_test_dependencies_for_uv(repo_root: Path) -> None:
    pyproject_path = repo_root / "backend" / "pyproject.toml"

    assert pyproject_path.is_file(), "backend/pyproject.toml must exist for uv-managed backend dependencies"

    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = pyproject.get("project", {})
    runtime_dependencies = project.get("dependencies", [])
    dependency_groups = pyproject.get("dependency-groups", {})

    test_group_names = [group_name for group_name in ("dev", "test") if group_name in dependency_groups]
    test_dependencies = [
        dependency
        for group_name in test_group_names
        for dependency in dependency_groups.get(group_name, [])
    ]

    assert any(dependency.startswith("fastapi") for dependency in runtime_dependencies)
    assert any(dependency.startswith("uvicorn") for dependency in runtime_dependencies)
    assert (
        test_group_names
    ), "backend/pyproject.toml must declare backend test dependencies in a uv dev/test dependency group"
    assert any(dependency.startswith("pytest") for dependency in test_dependencies)
    assert any(dependency.startswith("httpx") for dependency in test_dependencies)


def test_backend_uv_lockfile_is_committed_for_the_uv_managed_project(repo_root: Path) -> None:
    lockfile_path = repo_root / "backend" / "uv.lock"

    assert lockfile_path.is_file(), "backend/uv.lock must be committed for clean-checkout uv installs"

    tracked_lockfile = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "backend/uv.lock"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert tracked_lockfile.returncode == 0, "backend/uv.lock must be tracked in git, not left as an uncommitted local artifact"


def test_backend_uv_managed_project_removes_legacy_requirements_txt_contracts(repo_root: Path) -> None:
    legacy_requirements = [
        repo_root / "backend" / "requirements.txt",
        repo_root / "backend" / "tests" / "requirements.txt",
    ]

    legacy_contracts_still_present = [
        requirements_path.relative_to(repo_root).as_posix()
        for requirements_path in legacy_requirements
        if requirements_path.exists()
    ]

    assert (
        legacy_contracts_still_present == []
    ), "uv-managed backend dependency contracts should remove obsolete requirements.txt files"


def test_root_package_declares_a_modern_node_runtime_contract_for_frontend_tooling(
    package_json: dict,
) -> None:
    engines = package_json.get("engines", {})
    node_contract = engines.get("node")

    assert node_contract, "package.json must declare an engines.node runtime contract for the repo-level frontend toolchain"
    assert re.search(
        r"(?:^|[^\d])(20|2[1-9]|[3-9]\d)(?:[^\d]|$)",
        node_contract,
    ), "engines.node should explicitly target Node 20+ for the Vite/Vitest toolchain"


def test_vite_and_vitest_configs_use_module_filenames_under_a_commonjs_package_boundary(
    repo_root: Path,
    package_json: dict,
) -> None:
    assert (
        package_json.get("type") == "commonjs"
    ), "this contract applies only while the repo package boundary remains CommonJS"

    expected_module_configs = [repo_root / "vitest.config.mts", repo_root / "frontend" / "vite.config.mts"]
    legacy_ts_configs = [repo_root / "vitest.config.ts", repo_root / "frontend" / "vite.config.ts"]

    missing_module_configs = [
        config_path.relative_to(repo_root).as_posix()
        for config_path in expected_module_configs
        if not config_path.is_file()
    ]
    legacy_configs_still_present = [
        config_path.relative_to(repo_root).as_posix()
        for config_path in legacy_ts_configs
        if config_path.exists()
    ]

    assert missing_module_configs == [], "expected module-signaling config filenames are missing"
    assert (
        legacy_configs_still_present == []
    ), "legacy .ts Vite and Vitest config filenames should not remain under a CommonJS package boundary"
