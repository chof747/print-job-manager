import importlib

from fastapi.testclient import TestClient


def test_api_v1_namespace_returns_success() -> None:
    app_module = importlib.import_module("backend.app.main")
    client = TestClient(app_module.app)

    response = client.get("/api/v1")

    assert response.status_code == 200
