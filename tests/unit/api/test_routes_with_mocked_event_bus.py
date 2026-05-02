import importlib
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


class _Bus:
    def __init__(self, send_impl):
        self._send_impl = send_impl

    async def send(self, msg):
        return await self._send_impl(msg)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "test")

    sys.modules.pop("src.api.main", None)
    main = importlib.import_module("src.api.main")

    # Patch lifespan side-effects
    main.initialize_firebase = lambda: None  # type: ignore[assignment]

    async def _noop_async(*args, **kwargs):
        return None

    class _Scheduled:
        async def start(self):
            return None

        async def stop(self):
            return None

    main.initialize_cache_layer = _noop_async  # type: ignore[assignment]
    main.shutdown_cache_layer = _noop_async  # type: ignore[assignment]
    main.initialize_scheduled_notification_service = lambda: _Scheduled()  # type: ignore[assignment]

    from src.api.dependencies.auth import (
        get_current_user_id,
        verify_firebase_token,
        verify_firebase_uid_ownership,
    )
    from src.api.dependencies.event_bus import get_configured_event_bus
    from src.api.base_dependencies import get_image_store

    class _DummyImageStore:
        def get_url(self, image_id: str) -> str:
            return f"https://example.com/{image_id}"

    main.app.dependency_overrides[get_current_user_id] = lambda: "user_1"
    main.app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "firebase_1"}
    main.app.dependency_overrides[verify_firebase_uid_ownership] = (
        lambda firebase_uid="firebase_1": firebase_uid
    )
    main.app.dependency_overrides[get_image_store] = lambda: _DummyImageStore()

    # The specific send() behavior is set per-test by overriding get_configured_event_bus.
    yield TestClient(main.app)

    main.app.dependency_overrides = {}


def test_users_get_user_profile_by_firebase_uid(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    async def send(msg):
        return {
            "id": "user_1",
            "firebase_uid": "firebase_1",
            "email": "a@b.com",
            "username": "u",
            "first_name": None,
            "last_name": None,
            "phone_number": None,
            "display_name": None,
            "photo_url": None,
            "provider": "google",
            "is_active": True,
            "onboarding_completed": False,
            "last_accessed": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "has_subscription": False,
            "subscription": None,
        }

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    r = client.get("/v1/users/firebase/firebase_1")
    assert r.status_code == 200
    assert r.json()["firebase_uid"] == "firebase_1"


def test_users_get_onboarding_status(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    async def send(msg):
        return {
            "firebase_uid": "firebase_1",
            "onboarding_completed": False,
            "is_active": True,
            "last_accessed": None,
        }

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    r = client.get("/v1/users/firebase/firebase_1/status")
    assert r.status_code == 200
    assert r.json()["firebase_uid"] == "firebase_1"


def test_user_profiles_get_metrics(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    async def send(msg):
        return {
            "user_id": "user_1",
            "age": 25,
            "gender": "male",
            "height_cm": 170.0,
            "weight_kg": 70.0,
            "body_fat_percentage": None,
            "job_type": "desk",
            "training_days_per_week": 3,
            "training_minutes_per_session": 30,
            "training_level": None,
            "fitness_goal": "cut",
            "target_weight_kg": None,
            "updated_at": datetime.utcnow(),
        }

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    r = client.get("/v1/user-profiles/metrics")
    assert r.status_code == 200
    assert r.json()["user_id"] == "user_1"


def test_user_profiles_get_tdee(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    async def send(msg):
        # Handler expects a dict with profile_data + macros
        return {
            "bmr": 1700.0,
            "tdee": 2400.0,
            "profile_data": {"fitness_goal": "cut"},
            "macros": {
                "calories": 2400.0,
                "protein": 120.0,
                "carbs": 250.0,
                "fat": 70.0,
            },
            "activity_multiplier": 1.4,
            "formula_used": "Mifflin-St Jeor",
            "is_custom": False,
        }

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    r = client.get("/v1/user-profiles/tdee")
    assert r.status_code == 200
    assert r.json()["tdee"] == 2400.0


def test_meals_parse_text_happy_path(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    class _Item:
        def __init__(self, name, quantity, unit, protein, carbs, fat):
            self.name = name
            self.quantity = quantity
            self.unit = unit
            self.protein = protein
            self.carbs = carbs
            self.fat = fat
            self.fiber = 0.0
            self.data_source = "ai_estimate"
            self.fdc_id = None

    class _Resp:
        def __init__(self):
            self.items = [
                _Item("egg", 2, "piece", 12, 1, 10),
                _Item("toast", 1, "slice", 3, 12, 1),
            ]
            self.total_protein = 15
            self.total_carbs = 13
            self.total_fat = 11
            self.emoji = "🍳"

    async def send(msg):
        return _Resp()

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    r = client.post(
        "/v1/meals/parse-text", json={"text": "2 eggs and toast", "current_items": []}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["emoji"] == "🍳"
    assert len(body["items"]) == 2


def test_meals_manual_invalid_date_does_not_call_bus(monkeypatch, client: TestClient):
    from src.api.dependencies.event_bus import get_configured_event_bus
    import src.api.main as main

    called = {"send": 0}

    async def send(msg):
        called["send"] += 1
        return None

    main.app.dependency_overrides[get_configured_event_bus] = lambda: _Bus(send)

    payload = {
        "dish_name": "Manual meal",
        "meal_type": "lunch",
        "items": [
            {
                "fdc_id": 1,
                "name": "x",
                "quantity": 100,
                "unit": "g",
                "custom_nutrition": None,
            }
        ],
        "target_date": "2024-99-99",
        "source": "manual",
        "emoji": "🥗",
    }
    r = client.post("/v1/meals/manual", json=payload)
    assert r.status_code == 400
    assert called["send"] == 0
