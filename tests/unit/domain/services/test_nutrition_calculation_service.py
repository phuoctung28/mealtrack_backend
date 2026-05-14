from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.app.commands.meal.create_manual_meal_command import (
    CustomNutrition,
    ManualMealItem,
)
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal.food_item_change import (
    CustomNutritionData,
    FoodItemChange,
)
from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.services.meal_service import MealService
from src.domain.services.nutrition_calculation_service import (
    NutritionCalculationService,
)


def test_manual_custom_nutrition_uses_unit_grams_for_large_eggs():
    service = NutritionCalculationService()

    nutrition, food_items = service.aggregate_from_command_items(
        [
            ManualMealItem(
                name="Eggs",
                quantity=2.0,
                unit="large",
                custom_nutrition=CustomNutrition(
                    calories_per_100g=143.0,
                    protein_per_100g=12.6,
                    carbs_per_100g=0.7,
                    fat_per_100g=9.5,
                ),
            )
        ]
    )

    assert nutrition.macros.protein == pytest.approx(12.6)
    assert nutrition.macros.carbs == pytest.approx(0.7)
    assert nutrition.macros.fat == pytest.approx(9.5)
    assert food_items[0].calories == pytest.approx(138.7)


def test_manual_custom_nutrition_uses_density_for_oil_ml():
    service = NutritionCalculationService()

    nutrition, food_items = service.aggregate_from_command_items(
        [
            ManualMealItem(
                name="Cooking oil",
                quantity=5.0,
                unit="ml",
                custom_nutrition=CustomNutrition(
                    calories_per_100g=828.0,
                    protein_per_100g=0.0,
                    carbs_per_100g=0.0,
                    fat_per_100g=92.0,
                ),
            )
        ]
    )

    assert nutrition.macros.protein == pytest.approx(0.0)
    assert nutrition.macros.carbs == pytest.approx(0.0)
    assert nutrition.macros.fat == pytest.approx(4.2)
    assert food_items[0].macros.fat == pytest.approx(4.232)


def test_meal_service_add_custom_nutrition_uses_unit_grams():
    meal = _new_processing_meal()

    updated = MealService().apply_food_item_changes(
        meal,
        [
            FoodItemChange(
                action="add",
                name="Eggs",
                quantity=2.0,
                unit="large",
                custom_nutrition=CustomNutritionData(
                    calories_per_100g=143.0,
                    protein_per_100g=12.6,
                    carbs_per_100g=0.7,
                    fat_per_100g=9.5,
                ),
            )
        ],
    )

    assert updated.nutrition.macros.protein == pytest.approx(12.6)
    assert updated.nutrition.macros.carbs == pytest.approx(0.7)
    assert updated.nutrition.macros.fat == pytest.approx(9.5)


def _new_processing_meal() -> Meal:
    return Meal(
        id=uuid4(),
        user_id=uuid4(),
        status=MealStatus.PROCESSING,
        images=[
            MealImage(
                id=uuid4(),
                url="https://example.com/img.jpg",
                created_at=datetime.now(timezone.utc),
            )
        ],
        nutrition=Nutrition(
            foods=[],
            macros=Macros(protein=0.0, carbs=0.0, fat=0.0),
        ),
        consumed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
