def test_root_backend_dev_command_declares_a_static_uvicorn_entrypoint(package_json: dict) -> None:
    script = package_json["scripts"].get("dev:backend")

    assert script, "package.json must define a dev:backend root convenience command"
    assert "uvicorn" in script, "dev:backend should invoke the FastAPI backend through uvicorn"
    assert (
        "backend.app.main:app" in script
    ), "dev:backend should target the backend ASGI entrypoint from the repo root"
    assert (
        "pip install" not in script
    ), "dev:backend must not install dependencies; dependency setup belongs outside the repo command"


def test_root_backend_dev_command_runs_uvicorn_through_uv_from_the_repo_root(package_json: dict) -> None:
    script = package_json["scripts"].get("dev:backend")

    assert script, "package.json must define a dev:backend root convenience command"
    assert "uv run" in script, "dev:backend should execute uvicorn through uv so the backend pyproject contract owns dependency resolution"
    assert "backend" in script, "dev:backend should explicitly target the backend project when launched from the repo root"
    assert (
        "python3 -m uvicorn" not in script
    ), "dev:backend should not bypass uv by invoking uvicorn directly through the system Python"


def test_root_backend_check_command_declares_a_static_pytest_flow(package_json: dict) -> None:
    script = package_json["scripts"].get("check:backend")

    assert script, "package.json must define a check:backend root convenience command"
    assert "pytest" in script, "check:backend should run pytest through the root command"
    assert (
        "pip install" not in script
    ), "check:backend must not install dependencies; dependency setup belongs outside the repo check command"
    assert (
        "npm install" not in script
    ), "check:backend must not install dependencies; dependency setup belongs outside the repo check command"


def test_root_backend_check_command_runs_pytest_through_uv_from_the_repo_root(package_json: dict) -> None:
    script = package_json["scripts"].get("check:backend")

    assert script, "package.json must define a check:backend root convenience command"
    assert "uv run" in script, "check:backend should execute pytest through uv so the backend pyproject contract owns dependency resolution"
    assert "backend" in script, "check:backend should explicitly target the backend project when launched from the repo root"
    assert (
        "python3 -m pytest" not in script
    ), "check:backend should not bypass uv by invoking pytest directly through the system Python"


def test_root_frontend_dev_command_declares_a_static_vite_flow(package_json: dict) -> None:
    script = package_json["scripts"].get("dev:frontend")
    dependencies = package_json.get("dependencies", {})
    dev_dependencies = package_json.get("devDependencies", {})

    assert script, "package.json must define a dev:frontend root convenience command"
    assert "vite" in script, "dev:frontend should invoke the frontend through Vite"
    assert "frontend" in script, "dev:frontend should explicitly target the frontend app from the repo root"
    assert (
        "frontend/vite.config.mts" in script
    ), "dev:frontend should explicitly load the frontend Vite config from the repo root"
    assert (
        "pip install" not in script
    ), "dev:frontend must not install dependencies; dependency setup belongs outside the repo command"
    assert (
        "npm install" not in script
    ), "dev:frontend must not install dependencies; dependency setup belongs outside the repo command"
    assert (
        "vite" in dependencies or "vite" in dev_dependencies
    ), "dev:frontend should be backed by a declared vite dependency in package.json"


def test_root_frontend_check_command_declares_an_explicit_frontend_vitest_flow(
    package_json: dict,
) -> None:
    script = package_json["scripts"].get("check:frontend")

    assert script, "package.json must define a check:frontend root convenience command"
    assert "vitest" in script, "check:frontend should run Vitest through the root command"
    assert (
        "npm install" not in script
    ), "check:frontend must not install dependencies; dependency setup belongs outside the repo check command"
    assert (
        "frontend/" in script
    ), "check:frontend should explicitly scope Vitest to the frontend app from the repo root"
