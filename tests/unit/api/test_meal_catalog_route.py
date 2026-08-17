from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ExternalServiceException
from src.api.routes.v1 import meal_catalog as meal_catalog_route
from src.api.routes.v1.meal_catalog import router
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.app.queries.user import GetUserTimezoneQuery
from src.app.services.catalog_meal_browse_service import CatalogFeed
from src.domain.model.meal_recommendation import CatalogMeal, CatalogMealIngredient


def _meal() -> CatalogMeal:
    return CatalogMeal(
        id="catalog-1",
        catalog_key="catalog-1",
        content_hash="a" * 64,
        name="Japanese Egg Rice",
        cuisine="Japanese",
        description="A meal",
        image_url="https://example.test/meal.jpg",
        protein_g=Decimal("20"),
        carbs_g=Decimal("40"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("2"),
        sugar_g=Decimal("1"),
        meal_types=("breakfast",),
        ingredients=(
            CatalogMealIngredient(
                food_reference_id=7,
                display_name="Egg",
                quantity=Decimal("100"),
                unit="g",
            ),
        ),
        popularity_rank=1,
    )


class _Service:
    async def list_meals(self, **kwargs):
        assert kwargs["user_id"] == "user-1"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return SimpleNamespace(
            items=(_meal(),),
            total=1,
            feed=CatalogFeed.POPULAR,
            ranking_source="curated",
            fallback=False,
            allergy_evaluated=False,
        )

    async def get_meal(self, catalog_id):
        assert catalog_id == "catalog-1"
        return _meal()


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_configured_event_bus] = lambda: object()
    from src.api.base_dependencies import get_catalog_meal_browse_service

    app.dependency_overrides[get_catalog_meal_browse_service] = lambda: _Service()
    return app


def test_list_returns_mobile_catalog_projection_without_list_ingredients():
    response = TestClient(_app()).get("/v1/meal-catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id"] == "catalog-1"
    assert body["items"][0]["macros"]["protein_g"] == 20.0
    assert body["items"][0]["calories"] == 326
    assert body["items"][0]["meal_types"] == ["breakfast"]
    assert body["items"][0]["ingredient_count"] == 1
    assert body["items"][0]["ingredients"] == []
    assert body["feed"] == "popular"
    assert body["ranking_source"] == "curated"


def test_popular_list_does_not_initialize_event_bus(monkeypatch):
    def fail_event_bus():
        raise AssertionError("popular feed must not initialize event bus")

    monkeypatch.setattr(meal_catalog_route, "get_configured_event_bus", fail_event_bus)

    response = TestClient(_app()).get("/v1/meal-catalog")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_for_you_context_marks_weekly_budget_read_only():
    sent = []

    class _Bus:
        async def send(self, query):
            sent.append(query)
            if isinstance(query, GetUserTimezoneQuery):
                return "UTC"
            return {"adjusted_daily_calories": 2000}

    request = Request(
        {
            "type": "http",
            "headers": [(b"x-timezone", b"UTC")],
        }
    )
    context = await meal_catalog_route._personalization_context(
        request,
        user_id="user-1",
        event_bus=_Bus(),
    )

    assert context[2] == 2000
    budget_query = next(query for query in sent if isinstance(query, GetWeeklyBudgetQuery))
    assert budget_query.read_only is True


@pytest.mark.asyncio
async def test_for_you_context_falls_back_when_read_only_target_is_unavailable():
    class _Bus:
        async def send(self, query):
            if isinstance(query, GetUserTimezoneQuery):
                return "UTC"
            raise ExternalServiceException(
                "Authoritative target calculation is unavailable",
                "target_service_unavailable",
            )

    request = Request(
        {
            "type": "http",
            "headers": [(b"x-timezone", b"UTC")],
        }
    )

    context = await meal_catalog_route._personalization_context(
        request,
        user_id="user-1",
        event_bus=_Bus(),
    )

    assert context == (None, None, None)


def test_for_you_endpoint_falls_back_to_popular_when_target_is_unavailable(monkeypatch):
    class _Bus:
        async def send(self, query):
            if isinstance(query, GetUserTimezoneQuery):
                return "UTC"
            raise ExternalServiceException(
                "Authoritative target calculation is unavailable",
                "target_service_unavailable",
            )

    class _FallbackService:
        async def list_meals(self, **kwargs):
            assert kwargs["daily_calories"] is None
            assert kwargs["start_date"] is None
            assert kwargs["timezone"] is None
            return SimpleNamespace(
                items=(_meal(),),
                total=1,
                feed=CatalogFeed.POPULAR,
                ranking_source="curated",
                fallback=True,
                allergy_evaluated=False,
            )

    from src.api.base_dependencies import get_catalog_meal_browse_service

    app = _app()
    app.dependency_overrides[get_catalog_meal_browse_service] = (
        lambda: _FallbackService()
    )
    monkeypatch.setattr(meal_catalog_route, "get_configured_event_bus", lambda: _Bus())

    response = TestClient(app).get("/v1/meal-catalog?feed=for_you")

    assert response.status_code == 200
    assert response.json()["feed"] == "popular"
    assert response.json()["fallback"] is True


@pytest.mark.asyncio
async def test_for_you_context_propagates_unrelated_external_service_errors():
    class _Bus:
        async def send(self, query):
            if isinstance(query, GetUserTimezoneQuery):
                return "UTC"
            raise ExternalServiceException(
                "Catalog personalization failed",
                "catalog_personalization_unavailable",
            )

    request = Request(
        {
            "type": "http",
            "headers": [(b"x-timezone", b"UTC")],
        }
    )

    with pytest.raises(ExternalServiceException) as error:
        await meal_catalog_route._personalization_context(
            request,
            user_id="user-1",
            event_bus=_Bus(),
        )

    assert error.value.error_code == "catalog_personalization_unavailable"


def test_detail_returns_ingredient_identity_and_backend_calories():
    response = TestClient(_app()).get("/v1/meal-catalog/catalog-1")

    assert response.status_code == 200
    body = response.json()
    assert body["ingredients"] == [
        {
            "food_reference_id": 7,
            "display_name": "Egg",
            "quantity": 100.0,
            "unit": "g",
        }
    ]
    assert body["calories"] == 326


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=51", "offset=-1", "feed=invalid", "meal_type=brunch"],
)
def test_list_validates_catalog_query_contract(query):
    response = TestClient(_app()).get(f"/v1/meal-catalog?{query}")
    assert response.status_code == 422
