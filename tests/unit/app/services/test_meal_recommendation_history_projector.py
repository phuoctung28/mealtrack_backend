from datetime import UTC, datetime

import pytest

from src.app.services.meal_recommendation_history_projector import (
    MealRecommendationHistoryProjector,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientHistoryBucket,
)


class _MealRepo:
    def __init__(self, buckets):
        self.buckets = buckets
        self.call = None

    async def aggregate_linked_ingredient_history(self, **kwargs):
        self.call = kwargs
        return self.buckets

    async def find_by_date_range(self, **kwargs):
        raise AssertionError("history projector must use aggregate history")


class _Uow:
    def __init__(self, buckets):
        self.meals = _MealRepo(buckets)


@pytest.mark.asyncio
async def test_history_projector_uses_aggregate_linked_food_reference_buckets():
    uow = _Uow(
        [
            IngredientHistoryBucket(food_reference_id=11, age_days=1, capped_grams=120),
            IngredientHistoryBucket(food_reference_id=0, age_days=1, capped_grams=120),
        ]
    )

    profile = await MealRecommendationHistoryProjector().build_affinity(
        uow,
        user_id="user-1",
        start_date=datetime(2026, 7, 16, tzinfo=UTC).date(),
        timezone="UTC",
    )

    assert set(profile.weights) == {11}
    assert profile.confidence > 0
    assert uow.meals.call == {
        "user_id": "user-1",
        "start_date": datetime(2026, 4, 17, tzinfo=UTC).date(),
        "end_date": datetime(2026, 7, 15, tzinfo=UTC).date(),
        "user_timezone": "UTC",
        "reference_date": datetime(2026, 7, 16, tzinfo=UTC).date(),
    }
