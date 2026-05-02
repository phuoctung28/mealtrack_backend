import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Ensure predictable environment (don’t mount uploads)
    monkeypatch.setenv("ENVIRONMENT", "test")
    # Import a fresh app module instance and patch lifespan side-effects.
    # Other tests may import `src.api.main` with different ENVIRONMENT values.
    import sys
    import importlib

    sys.modules.pop("src.api.main", None)
    main = importlib.import_module("src.api.main")

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

    # Dependency overrides to avoid DB/event bus initialization
    from src.api.dependencies.auth import get_current_user_id, verify_firebase_token
    from src.api.dependencies.event_bus import get_configured_event_bus
    from src.api.base_dependencies import get_image_store

    class _DummyBus:
        async def send(self, msg):
            raise AssertionError("event_bus.send should not be called in these smoke tests")

    class _DummyImageStore:
        def get_url(self, image_id: str) -> str:
            return f"https://example.com/{image_id}"

    main.app.dependency_overrides[get_current_user_id] = lambda: "user_1"
    main.app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "user_1"}
    main.app.dependency_overrides[get_configured_event_bus] = lambda: _DummyBus()
    main.app.dependency_overrides[get_image_store] = lambda: _DummyImageStore()

    with TestClient(main.app) as c:
        yield c

    main.app.dependency_overrides = {}


def test_openapi_json_available(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "MealTrack API"


def test_meals_analyze_rejects_invalid_file_type(client: TestClient):
    r = client.post(
        "/v1/meals/image/analyze",
        files={"file": ("x.gif", b"abc", "image/gif")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "INVALID_FILE_TYPE"


def test_meals_analyze_rejects_invalid_target_date(client: TestClient):
    r = client.post(
        "/v1/meals/image/analyze?target_date=2024-99-99",
        files={"file": ("x.jpg", b"abc", "image/jpeg")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "INVALID_DATE_FORMAT"


def test_meals_analyze_rejects_too_large(monkeypatch, client: TestClient):
    # Avoid allocating 10MB in tests by shrinking limit
    import src.api.routes.v1.meals as meals_routes

    monkeypatch.setattr(meals_routes, "MAX_FILE_SIZE", 3)

    r = client.post(
        "/v1/meals/image/analyze",
        files={"file": ("x.jpg", b"abcd", "image/jpeg")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "FILE_SIZE_EXCEEDS_MAXIMUM"


def test_user_profiles_onboarding_invalid_birth_date(client: TestClient):
    payload = {
        "birth_year": 2000,
        "birth_month": 2,
        "birth_day": 31,  # invalid
        "gender": "male",
        "height": 170,
        "weight": 70,
        "body_fat_percentage": None,
        "job_type": "desk",
        "training_days_per_week": 3,
        "training_minutes_per_session": 30,
        "goal": "cut",
        "pain_points": [],
        "dietary_preferences": [],
        "meals_per_day": 3,
        "referral_sources": [],
    }
    r = client.post("/v1/user-profiles/", json=payload)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid birth date"


def test_users_sync_forbidden_when_token_uid_mismatch(client: TestClient):
    # Override token to mismatch the request.firebase_uid
    import src.api.main as main
    from src.api.dependencies.auth import verify_firebase_token

    main.app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "uid_token"}

    payload = {
        "firebase_uid": "uid_request",
        "email": "a@b.com",
        "phone_number": None,
        "display_name": None,
        "photo_url": None,
        "provider": "google",
        "username": None,
        "first_name": None,
        "last_name": None,
    }
    r = client.post("/v1/users/sync", json=payload)
    assert r.status_code == 403

