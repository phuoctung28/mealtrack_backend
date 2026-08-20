"""Auth and abuse-control contracts for provider-backed food routes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.auth import get_current_user_id
from src.api.routes.v1 import feature_flags, foods
from src.api.schemas.response.barcode_product_response import BarcodeProductResponse


def _app(*, authenticated: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(foods.router)
    app.include_router(feature_flags.router)
    if authenticated:
        app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    return app


def test_provider_backed_food_reads_require_authentication():
    client = TestClient(_app(authenticated=False))

    for path in (
        "/v1/foods/search?q=rice",
        "/v1/foods/autocomplete?q=ri",
        "/v1/foods/123/details",
        "/v1/foods/barcode/036000291452",
        "/v1/feature-flags/",
    ):
        response = client.get(path)
        assert response.status_code == 401


def test_food_route_limit_constants_are_bounded():
    assert foods.FOOD_SEARCH_LIMIT == "30/minute"
    assert foods.FOOD_AUTOCOMPLETE_LIMIT == "60/minute"
    assert foods.FOOD_DETAILS_LIMIT == "30/minute"
    assert foods.FOOD_BARCODE_LIMIT == "20/minute"


def test_provider_backed_food_routes_are_limiter_wrapped():
    for route in (
        foods.search_foods,
        foods.autocomplete_foods,
        foods.get_food_details,
        foods.lookup_barcode,
    ):
        assert getattr(route, "__wrapped__", None) is not None


def test_barcode_response_preserves_provider_identity():
    response = BarcodeProductResponse(
        name="Whole Grain Cheerios",
        barcode="036000291452",
        origin="provider",
        source_namespace="fatsecret",
        source_food_id="50953",
    )

    payload = response.model_dump()

    assert payload["origin"] == "provider"
    assert payload["source_namespace"] == "fatsecret"
    assert payload["source_food_id"] == "50953"
