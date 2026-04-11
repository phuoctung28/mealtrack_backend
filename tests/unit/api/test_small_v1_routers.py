"""Thin v1 routers: foods, activities, cheat_days, ingredients — mocked buses / auth."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.auth import get_current_user_id
from src.api.exceptions import ValidationException
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.routes.v1 import activities as activities_mod
from src.api.routes.v1 import cheat_days as cheat_days_mod
from src.api.routes.v1 import foods as foods_mod
from src.api.routes.v1 import ingredients as ingredients_mod


class _Bus:
    def __init__(self, result):
        self._result = result
        self.sent = []

    async def send(self, msg):
        self.sent.append(msg)
        return self._result


@pytest.fixture
def foods_app():
    app = FastAPI()
    app.include_router(foods_mod.router)
    return app


def test_foods_search(foods_app, monkeypatch):
    bus = _Bus({"query": "rice", "results": [], "total": 0})
    monkeypatch.setattr(foods_mod, "get_food_search_event_bus", lambda: bus)
    r = TestClient(foods_app).get("/v1/foods/search?q=rice")
    assert r.status_code == 200
    assert r.json()["query"] == "rice"


def test_foods_search_500(foods_app, monkeypatch):
    class _Bad:
        async def send(self, msg):
            raise RuntimeError("down")

    monkeypatch.setattr(foods_mod, "get_food_search_event_bus", lambda: _Bad())
    r = TestClient(foods_app).get("/v1/foods/search?q=x")
    assert r.status_code == 500


def test_foods_details(foods_app, monkeypatch):
    bus = _Bus({"name": "Apple"})
    monkeypatch.setattr(foods_mod, "get_food_search_event_bus", lambda: bus)
    r = TestClient(foods_app).get("/v1/foods/123/details")
    assert r.status_code == 200
    assert r.json()["name"] == "Apple"


def test_foods_barcode_found(foods_app, monkeypatch):
    bus = _Bus(
        {
            "barcode": "123",
            "name": "Product",
            "brand": None,
            "protein_100g": 1.0,
            "carbs_100g": 2.0,
            "fat_100g": 3.0,
            "fiber_100g": 0.0,
            "sugar_100g": 0.0,
            "serving_size": "100g",
            "image_url": None,
        }
    )
    monkeypatch.setattr(foods_mod, "get_food_search_event_bus", lambda: bus)
    foods_app.dependency_overrides[get_current_user_id] = lambda: "u1"
    r = TestClient(foods_app).get("/v1/foods/barcode/123")
    assert r.status_code == 200


def test_foods_barcode_404(foods_app, monkeypatch):
    bus = _Bus(None)
    monkeypatch.setattr(foods_mod, "get_food_search_event_bus", lambda: bus)
    foods_app.dependency_overrides[get_current_user_id] = lambda: "u1"
    r = TestClient(foods_app).get("/v1/foods/barcode/unknown")
    assert r.status_code == 404


@pytest.fixture
def activities_app():
    app = FastAPI()
    app.include_router(activities_mod.router)
    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    return app


def test_activities_daily_default_date(activities_app):
    bus = _Bus([])
    activities_app.dependency_overrides[get_configured_event_bus] = lambda: bus
    r = TestClient(activities_app).get("/v1/activities/daily")
    assert r.status_code == 200
    assert r.json() == []


def test_activities_daily_invalid_date(activities_app):
    activities_app.dependency_overrides[get_configured_event_bus] = lambda: _Bus([])
    r = TestClient(activities_app).get("/v1/activities/daily?date=bad")
    assert r.status_code == 400


@pytest.fixture
def cheat_app():
    app = FastAPI()
    app.include_router(cheat_days_mod.router)
    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    return app


def test_cheat_mark_and_list(cheat_app):
    bus = _Bus({"ok": True})
    cheat_app.dependency_overrides[get_configured_event_bus] = lambda: bus
    r = TestClient(cheat_app).post("/v1/cheat-days?date=2025-06-15")
    assert r.status_code == 200

    r2 = TestClient(cheat_app).get("/v1/cheat-days")
    assert r2.status_code == 200


def test_cheat_invalid_date_post(cheat_app):
    cheat_app.dependency_overrides[get_configured_event_bus] = lambda: _Bus({})
    with pytest.raises(ValidationException):
        TestClient(cheat_app).post("/v1/cheat-days?date=not-a-date")


def test_cheat_delete_and_week(cheat_app):
    bus = _Bus(True)
    cheat_app.dependency_overrides[get_configured_event_bus] = lambda: bus
    r = TestClient(cheat_app).delete("/v1/cheat-days/2025-06-10")
    assert r.status_code == 200

    r2 = TestClient(cheat_app).get("/v1/cheat-days?week_of=2025-06-10")
    assert r2.status_code == 200


@pytest.fixture
def ingredients_app():
    app = FastAPI()
    app.include_router(ingredients_mod.router)
    return app


def test_ingredients_recognize(ingredients_app):
    bus = _Bus(
        {
            "name": "tomato",
            "confidence": 0.9,
            "category": "vegetable",
            "success": True,
            "message": None,
        }
    )
    ingredients_app.dependency_overrides[get_configured_event_bus] = lambda: bus
    r = TestClient(ingredients_app).post(
        "/v1/ingredients/recognize",
        json={"image_data": "abc"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "tomato"


def test_ingredients_health(ingredients_app):
    r = TestClient(ingredients_app).get("/v1/ingredients/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
