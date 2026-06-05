from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1.movement import router


def test_movement_catalog_route_returns_activities(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    async def fake_user_id():
        return "user-1"

    class FakeBus:
        async def send(self, query):
            return {"activities": [{"id": "badminton", "met": {"moderate": 7.0}}]}

    from src.api.dependencies.auth import get_current_user_id
    from src.api.dependencies.event_bus import get_configured_event_bus

    app.dependency_overrides[get_current_user_id] = fake_user_id
    app.dependency_overrides[get_configured_event_bus] = lambda: FakeBus()

    response = TestClient(app).get("/v1/movement/catalog")

    assert response.status_code == 200
    assert response.json()["activities"][0]["id"] == "badminton"
