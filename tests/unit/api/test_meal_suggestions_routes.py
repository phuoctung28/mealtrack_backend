"""Cover meal_suggestions routes with TestClient + rate limiter state."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.middleware.rate_limit import limiter
from src.api.routes.v1 import meal_suggestions as ms_mod
from src.domain.model.meal_suggestion.meal_suggestion import (
    MacroEstimate,
    MealSuggestion,
    MealType,
)
from src.domain.model.meal_suggestion.suggestion_session import SuggestionSession


class _BusOk:
    async def send(self, msg):
        session = SuggestionSession(
            id="sess-1",
            user_id="user-1",
            meal_type="lunch",
            meal_portion_type="main",
            target_calories=500,
            ingredients=[],
            cooking_time_minutes=30,
        )
        sug = MealSuggestion(
            id="s1",
            session_id="sess-1",
            user_id="user-1",
            meal_name="Test Bowl",
            description="d",
            meal_type=MealType.LUNCH,
            macros=MacroEstimate(calories=400, protein=30, carbs=40, fat=12),
            ingredients=[],
            recipe_steps=[],
            prep_time_minutes=15,
            confidence_score=0.9,
        )
        return session, [sug]


@pytest.fixture
def ms_client():
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(ms_mod.router)
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    bus = _BusOk()
    app.dependency_overrides[get_configured_event_bus] = lambda: bus
    yield TestClient(app), bus
    app.dependency_overrides = {}


def test_generate_meal_suggestions_ok(ms_client):
    client, _bus = ms_client
    payload = {
        "meal_type": "lunch",
        "meal_portion_type": "main",
        "ingredients": ["chicken"],
        "cooking_time_minutes": 30,
    }
    r = client.post("/v1/meal-suggestions/generate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "sess-1"
    assert len(body["suggestions"]) == 1


def test_save_meal_suggestion_ok(ms_client):
    client, bus = ms_client

    class _BusSave:
        async def send(self, msg):
            return "meal-uuid-1"

    # replace bus on app
    client.app.dependency_overrides[get_configured_event_bus] = lambda: _BusSave()

    payload = {
        "suggestion_id": "s1",
        "name": "Saved",
        "meal_type": "lunch",
        "protein": 10.0,
        "carbs": 20.0,
        "fat": 5.0,
        "ingredients": [],
        "instructions": [],
        "meal_date": "2026-04-11",
    }
    r = client.post("/v1/meal-suggestions/save", json=payload)
    assert r.status_code == 200
    assert r.json()["meal_id"] == "meal-uuid-1"


def test_generate_suggestions_handle_exception(ms_client):
    client, _bus = ms_client

    class _BusErr:
        async def send(self, msg):
            raise RuntimeError("pipeline")

    client.app.dependency_overrides[get_configured_event_bus] = lambda: _BusErr()

    payload = {
        "meal_type": "dinner",
        "meal_portion_type": "main",
        "ingredients": ["rice"],
        "cooking_time_minutes": 45,
    }
    r = client.post("/v1/meal-suggestions/generate", json=payload)
    assert r.status_code == 500
