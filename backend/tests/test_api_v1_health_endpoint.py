import importlib

from fastapi.testclient import TestClient


def test_api_v1_health_endpoint_returns_success() -> None:
    app_module = importlib.import_module("backend.app.main")
    client = TestClient(app_module.app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_health_endpoint_allows_browser_requests_from_configured_frontend_origin(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PRINT_JOB_MANAGER_FRONTEND_ORIGIN", "https://frontend.example.test")
    app_module = importlib.import_module("backend.app.main")
    app_module = importlib.reload(app_module)
    client = TestClient(app_module.app)

    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://frontend.example.test"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example.test"
