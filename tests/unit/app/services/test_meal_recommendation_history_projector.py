from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.app.services.meal_recommendation_history_projector import (
    MealRecommendationHistoryProjector,
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import FoodItem, Macros, Nutrition


class _MealRepo:
    def __init__(self, meals):
        self.meals = meals
        self.call = None

    async def find_by_date_range(self, **kwargs):
        self.call = kwargs
        return self.meals


class _Uow:
    def __init__(self, meals):
        self.meals = _MealRepo(meals)


def _meal(food_reference_id: int | None) -> Meal:
    return Meal(
        meal_id=str(uuid4()),
        user_id=str(uuid4()),
        status=MealStatus.READY,
        created_at=datetime(2026, 7, 10, tzinfo=UTC),
        ready_at=datetime(2026, 7, 10, tzinfo=UTC),
        image=None,
        nutrition=Nutrition(
            macros=Macros(protein=20, carbs=30, fat=10),
            food_items=[
                FoodItem(
                    id=str(uuid4()),
                    name="Ingredient",
                    quantity=120,
                    unit="g",
                    macros=Macros(protein=10, carbs=10, fat=5),
                    food_reference_id=food_reference_id,
                )
            ],
        ),
    )


@pytest.mark.asyncio
async def test_history_projector_uses_recent_linked_food_reference_events():
    uow = _Uow([_meal(11), _meal(None)])

    profile = await MealRecommendationHistoryProjector().build_affinity(
        uow,
        user_id="user-1",
        start_date=datetime(2026, 7, 16, tzinfo=UTC).date(),
        timezone="UTC",
    )

    assert set(profile.weights) == {11}
    assert profile.confidence > 0
    assert uow.meals.call["limit"] == 5000
