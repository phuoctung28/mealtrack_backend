from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1.health import router


def test_health_accepts_head_requests():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).head("/health")

    assert response.status_code == 200
