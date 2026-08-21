"""Auth and abuse-control contracts for provider-backed food routes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.auth import get_current_user_id
from src.api.exception_handlers import register_exception_handlers
from src.api.exceptions import ExternalServiceException
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


def test_barcode_identity_failure_is_retryable_503(monkeypatch):
    app = _app(authenticated=True)
    register_exception_handlers(app)

    class _EventBus:
        async def send(self, _query):
            raise ExternalServiceException(
                "Barcode nutrition identity is temporarily unavailable. Please retry.",
                error_code="BARCODE_SOURCE_IDENTITY_UNAVAILABLE",
            )

    monkeypatch.setattr(foods, "get_food_search_event_bus", lambda: _EventBus())
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/v1/foods/barcode/036000291452")

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == (
        "BARCODE_SOURCE_IDENTITY_UNAVAILABLE"
    )
