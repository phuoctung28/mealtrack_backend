from datetime import datetime, timezone

import pytest

from src.app.handlers.query_handlers.get_daily_hydration_query_handler import (
    _build_entry_dict,
)
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.model.nutrition.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros


def test_daily_hydration_entry_exposes_calories_for_caloric_drinks():
    logged_at = datetime(2026, 5, 26, 11, 0, tzinfo=timezone.utc)
    meal = Meal(
        meal_id="11111111-1111-1111-1111-111111111111",
        user_id="22222222-2222-2222-2222-222222222222",
        status=MealStatus.READY,
        created_at=logged_at,
        ready_at=logged_at,
        image=MealImage(
            image_id="33333333-3333-3333-3333-333333333333",
            format="jpeg",
            size_bytes=1,
            url=None,
        ),
        dish_name="Soda",
        emoji="🥤",
        meal_type="hydration",
        source="hydration",
        quantity=330,
        nutrition=Nutrition(
            macros=Macros(protein=0.0, carbs=35.0, fat=0.0, fiber=0.0, sugar=35.0),
            food_items=None,
        ),
    )

    entry = _build_entry_dict(meal)

    assert entry["kcal"] == pytest.approx(140.0)
    assert entry["calories"] == pytest.approx(140.0)


def test_daily_hydration_entry_localizes_static_drink_name():
    logged_at = datetime(2026, 5, 26, 11, 0, tzinfo=timezone.utc)
    meal = Meal(
        meal_id="11111111-1111-1111-1111-111111111111",
        user_id="22222222-2222-2222-2222-222222222222",
        status=MealStatus.READY,
        created_at=logged_at,
        ready_at=logged_at,
        image=MealImage(
            image_id="33333333-3333-3333-3333-333333333333",
            format="jpeg",
            size_bytes=1,
            url=None,
        ),
        dish_name="Fruit juice",
        emoji="🧃",
        meal_type="hydration",
        source="hydration",
        quantity=333,
        nutrition=Nutrition(
            macros=Macros(protein=0.0, carbs=30.8, fat=3.4, fiber=0.0, sugar=30.8),
            food_items=None,
        ),
    )

    entry = _build_entry_dict(meal, language="vi")

    assert entry["drink_name"] == "Nước ép"
