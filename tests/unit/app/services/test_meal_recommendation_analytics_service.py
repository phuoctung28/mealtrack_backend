from datetime import date

import pytest

from src.app.services.meal_recommendation_analytics_service import (
    MealRecommendationAnalyticsService,
)
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan


class _Adapter:
    def __init__(self):
        self.payloads = []

    async def capture(self, *, distinct_id, event, properties):
        self.payloads.append(
            {
                "distinct_id": distinct_id,
                "event": event,
                "properties": properties,
            }
        )


def _plan() -> PersistedMealRecommendationPlan:
    return PersistedMealRecommendationPlan(
        id="plan-1",
        user_id="user-1",
        status="active",
        timezone="UTC",
        start_date=date(2026, 7, 16),
        daily_calories=2000,
        algorithm_version="catalog_deterministic_v1",
        operation="three_day",
        idempotency_key="key-1",
        request_fingerprint="f" * 64,
    )


@pytest.mark.asyncio
async def test_analytics_uses_pseudonymous_id_and_bounded_properties():
    adapter = _Adapter()
    service = MealRecommendationAnalyticsService(salt="salt", adapter=adapter)

    await service.capture_plan_response(
        user_id="raw-user-id",
        event="plan_shown",
        plan=_plan(),
    )

    payload = adapter.payloads[0]
    assert payload["distinct_id"].startswith("meal-rec-v1:")
    assert payload["distinct_id"] != "raw-user-id"
    assert payload["event"] == "plan_shown"
    assert set(payload["properties"]) == {
        "schema_version",
        "algorithm_version",
        "slots_count",
        "alternatives_count",
    }


@pytest.mark.asyncio
async def test_analytics_disabled_without_salt():
    adapter = _Adapter()
    service = MealRecommendationAnalyticsService(salt="", adapter=adapter)

    await service.capture_plan_response(
        user_id="user-1",
        event="plan_shown",
        plan=_plan(),
    )

    assert adapter.payloads == []
