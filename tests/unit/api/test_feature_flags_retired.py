from fastapi.testclient import TestClient

from src.api.main import app


def test_feature_flag_routes_are_not_registered():
    assert all(not route.path.startswith("/v1/feature-flags") for route in app.routes)


def test_feature_flag_endpoint_returns_not_found():
    response = TestClient(app).get("/v1/feature-flags/")

    assert response.status_code == 404
