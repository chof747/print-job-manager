import importlib

from fastapi.testclient import TestClient


def test_api_v1_config_endpoint_returns_shell_config() -> None:
    app_module = importlib.import_module("backend.app.main")
    client = TestClient(app_module.app)

    response = client.get("/api/v1/config")

    assert response.status_code == 200
    assert response.json() == {
        "appName": "print-job-manager",
        "apiBasePath": "/api/v1",
    }
