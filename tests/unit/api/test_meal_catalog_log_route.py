from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from src.api.routes.v1.meal_catalog import router as catalog_router
from src.api.routes.v1.meal_catalog_log import router as catalog_log_router
from src.app.commands.meal_catalog import LogCatalogMealCommand
from src.app.queries.meal_catalog import ListLoggedCatalogMealsQuery
from src.app.queries.user import GetUserTimezoneQuery
from src.app.services.catalog_meal_log_service import LogCatalogMealResult
from src.domain.model.meal_recommendation import CatalogMeal


def _meal() -> CatalogMeal:
    return CatalogMeal(
        id="catalog-1",
        catalog_key="catalog-1",
        content_hash="a" * 64,
        name="Egg Rice",
        cuisine="Japanese",
        description=None,
        image_url=None,
        protein_g=Decimal("20"),
        carbs_g=Decimal("40"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("2"),
        meal_types=("breakfast",),
    )


class _Bus:
    def __init__(self, meals=None):
        self.commands = []
        self.meals = meals or []

    async def send(self, item):
        self.commands.append(item)
        if isinstance(item, GetUserTimezoneQuery):
            return "UTC"
        if isinstance(item, ListLoggedCatalogMealsQuery):
            return self.meals
        if isinstance(item, LogCatalogMealCommand):
            meal = SimpleNamespace(
                meal_id="meal-1", dish_name="Egg Rice", nutrition=None
            )
            return LogCatalogMealResult(
                meal_id="meal-1",
                catalog_meal_id=item.catalog_meal_id,
                logged_via="catalog",
                plan_id=None,
                slot_id=None,
                meal_date=item.meal_date,
                meal_type=item.meal_type,
                meal=meal,
            )
        raise AssertionError(type(item))


def _app(bus=None) -> FastAPI:
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.include_router(catalog_log_router)
    app.include_router(catalog_router)
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_configured_event_bus] = lambda: bus or _Bus()
    return app


def test_logged_route_is_not_captured_as_catalog_id():
    app = _app()
    routes = {route.path: route for route in app.routes if hasattr(route, "path")}
    assert "/v1/meal-catalog/logged" in routes
    response = TestClient(app).get("/v1/meal-catalog/logged")
    assert response.status_code == 200
    assert response.json() == {"items": [], "limit": 20}


def test_logged_requires_auth():
    app = _app()
    app.dependency_overrides.pop(get_current_user_id)

    response = TestClient(app).get("/v1/meal-catalog/logged")

    assert response.status_code in {401, 403, 422}


def test_logged_strips_ingredients_and_is_owner_query():
    bus = _Bus(meals=[_meal()])
    response = TestClient(_app(bus)).get("/v1/meal-catalog/logged?limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id"] == "catalog-1"
    assert body["items"][0]["ingredients"] == []
    query = bus.commands[0]
    assert isinstance(query, ListLoggedCatalogMealsQuery)
    assert query.user_id == "user-1"


def test_logged_rejects_limit_over_50():
    response = TestClient(_app()).get("/v1/meal-catalog/logged?limit=51")
    assert response.status_code == 422


def test_log_requires_auth():
    app = _app()
    app.dependency_overrides.pop(get_current_user_id)
    response = TestClient(app).post(
        "/v1/meal-catalog/catalog-1/log",
        json={
            "request_id": "req-1",
            "meal_date": "2026-08-18",
            "meal_type": "breakfast",
        },
    )
    assert response.status_code in {401, 403, 422}


def test_log_rejects_bad_meal_type_and_date():
    client = TestClient(_app())
    bad_type = client.post(
        "/v1/meal-catalog/catalog-1/log",
        json={
            "request_id": "req-1",
            "meal_date": "2026-08-18",
            "meal_type": "brunch",
        },
    )
    bad_date = client.post(
        "/v1/meal-catalog/catalog-1/log",
        json={
            "request_id": "req-1",
            "meal_date": "18-08-2026",
            "meal_type": "breakfast",
        },
    )
    assert bad_type.status_code == 422
    assert bad_date.status_code == 422


def test_log_returns_locked_response_shape():
    bus = _Bus()
    response = TestClient(_app(bus)).post(
        "/v1/meal-catalog/catalog-1/log",
        json={
            "request_id": "req-1",
            "meal_date": "2026-08-18",
            "meal_type": "breakfast",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "meal_id": "meal-1",
        "catalog_meal_id": "catalog-1",
        "logged_via": "catalog",
        "plan_id": None,
        "slot_id": None,
        "logged_meal_id": "meal-1",
        "meal_date": "2026-08-18",
        "meal_type": "breakfast",
    }
    command = next(
        item for item in bus.commands if isinstance(item, LogCatalogMealCommand)
    )
    assert command.user_id == "user-1"
    assert command.catalog_meal_id == "catalog-1"
    assert command.meal_date == date(2026, 8, 18)
