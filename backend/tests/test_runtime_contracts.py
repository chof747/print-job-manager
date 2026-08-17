from pathlib import Path
import re


def test_backend_runtime_and_test_requirements_declare_the_shell_stack(repo_root: Path) -> None:
    backend_requirements = (repo_root / "backend" / "requirements.txt").read_text(encoding="utf-8")
    backend_test_requirements = (repo_root / "backend" / "tests" / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert "fastapi==" in backend_requirements
    assert "uvicorn==" in backend_requirements
    assert "pytest==" in backend_test_requirements
    assert "fastapi==" in backend_test_requirements
    assert "httpx==" in backend_test_requirements


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
