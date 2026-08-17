import importlib

from fastapi.testclient import TestClient


def test_ready_endpoint_returns_success() -> None:
    app_module = importlib.import_module("backend.app.main")
    client = TestClient(app_module.app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
