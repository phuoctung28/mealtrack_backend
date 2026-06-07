from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1.health import root_router, router


def test_health_accepts_head_requests():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).head("/v1/health")

    assert response.status_code == 200


def test_root_health_accepts_head_requests():
    app = FastAPI()
    app.include_router(root_router)

    response = TestClient(app).head("/health")

    assert response.status_code == 200


def test_root_health_matches_versioned_health():
    app = FastAPI()
    app.include_router(root_router)
    app.include_router(router)
    client = TestClient(app)

    root_response = client.get("/health")
    versioned_response = client.get("/v1/health")

    assert root_response.status_code == 200
    assert root_response.json() == versioned_response.json()


def test_health_exposes_deployment_identity(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "1e1170b7")
    monkeypatch.setenv("RENDER_GIT_BRANCH", "fix/ios-time-sensitive-notifications")
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/v1/health")

    assert response.status_code == 200
    deployment = response.json()["deployment"]
    assert deployment["git_commit"] == "1e1170b7"
    assert deployment["git_branch"] == "fix/ios-time-sensitive-notifications"
