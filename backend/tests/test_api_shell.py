import importlib

from fastapi.testclient import TestClient


def test_health_endpoint_returns_success(shell_client: TestClient) -> None:
    response = shell_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_returns_success(shell_client: TestClient) -> None:
    response = shell_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_namespace_returns_success(shell_client: TestClient) -> None:
    response = shell_client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_health_endpoint_returns_success(shell_client: TestClient) -> None:
    response = shell_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_config_endpoint_returns_shell_config(shell_client: TestClient) -> None:
    response = shell_client.get("/api/v1/config")

    assert response.status_code == 200
    assert response.json() == {
        "appName": "print-job-manager",
        "apiBasePath": "/api/v1",
    }


def test_api_v1_health_endpoint_allows_browser_requests_from_configured_frontend_origin(
    monkeypatch,
) -> None:
    from backend.app import config as app_config

    app_module = importlib.import_module("backend.app.main")
    try:
        with monkeypatch.context() as frontend_origin:
            frontend_origin.setenv(
                "PRINT_JOB_MANAGER_FRONTEND_ORIGIN", "https://frontend.example.test"
            )
            app_config.get_settings.cache_clear()
            app_module = importlib.reload(app_module)

            with TestClient(app_module.app) as client:
                response = client.get(
                    "/api/v1/health",
                    headers={"Origin": "https://frontend.example.test"},
                )

            assert response.status_code == 200
            assert (
                response.headers["access-control-allow-origin"]
                == "https://frontend.example.test"
            )
    finally:
        app_config.get_settings.cache_clear()
        importlib.reload(app_module)
