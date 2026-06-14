"""Tests for canonical AI nutrition output contracts."""

import pytest
from pydantic import ValidationError

from src.domain.model.ai.nutrition_contracts import (
    AINutritionMacros,
    MealTextNutritionResponse,
    VisionNutritionResponse,
)


def _valid_macros() -> dict[str, float]:
    return {
        "protein_g": 35.0,
        "carbs_g": 42.0,
        "fat_g": 12.0,
        "fiber_g": 4.0,
        "sugar_g": 3.0,
    }


class TestAINutritionMacros:
    def test_accepts_macro_grams(self):
        macros = AINutritionMacros.model_validate(_valid_macros())

        assert macros.protein_g == pytest.approx(35.0)
        assert macros.fiber_g == pytest.approx(4.0)
        assert macros.sugar_g == pytest.approx(3.0)

    def test_defaults_optional_fiber_and_sugar_to_zero(self):
        macros = AINutritionMacros.model_validate(
            {"protein_g": 10.0, "carbs_g": 20.0, "fat_g": 5.0}
        )

        assert macros.fiber_g == pytest.approx(0.0)
        assert macros.sugar_g == pytest.approx(0.0)

    def test_rejects_negative_macros(self):
        with pytest.raises(ValidationError):
            AINutritionMacros.model_validate(
                {"protein_g": -1.0, "carbs_g": 20.0, "fat_g": 5.0}
            )


class TestVisionNutritionResponse:
    def test_accepts_realistic_food_quantities(self):
        response = VisionNutritionResponse.model_validate(
            {
                "dish_name": "Chicken rice bowl",
                "foods": [
                    {
                        "name": "Grilled chicken",
                        "quantity_g": 150.0,
                        "macros": _valid_macros(),
                        "confidence": 0.92,
                    }
                ],
                "confidence": 0.88,
                "calories": 9999,
            }
        )

        assert response.dish_name == "Chicken rice bowl"
        assert response.is_food is True
        assert response.foods[0].quantity_g == pytest.approx(150.0)
        assert response.foods[0].macros.protein_g == pytest.approx(35.0)
        assert "calories" not in response.model_dump()

    def test_accepts_non_food_with_empty_foods(self):
        response = VisionNutritionResponse.model_validate(
            {
                "is_food": False,
                "dish_name": None,
                "foods": [],
                "confidence": 0.95,
            }
        )

        assert response.is_food is False
        assert response.foods == []

    def test_rejects_impossible_quantity_g(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "foods": [
                        {
                            "name": "Rice",
                            "quantity_g": 150000.0,
                            "macros": _valid_macros(),
                        }
                    ]
                }
            )

    def test_rejects_empty_food_name(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "foods": [
                        {
                            "name": " ",
                            "quantity_g": 120.0,
                            "macros": _valid_macros(),
                        }
                    ]
                }
            )

    def test_rejects_more_than_eight_foods(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "foods": [
                        {
                            "name": f"Food {index}",
                            "quantity_g": 10.0,
                            "macros": _valid_macros(),
                        }
                        for index in range(9)
                    ]
                }
            )

    def test_rejects_empty_foods_when_is_food_defaults_true(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate({"foods": []})

    def test_rejects_missing_foods(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate({"dish_name": "Unknown meal"})


class TestMealTextNutritionResponse:
    def test_accepts_display_quantity_unit_and_optional_quantity_g(self):
        response = MealTextNutritionResponse.model_validate(
            {
                "emoji": "🍜",
                "items": [
                    {
                        "name": "Pho",
                        "quantity": 1.0,
                        "unit": "bowl",
                        "english_unit": "bowl",
                        "quantity_g": 550.0,
                        "macros": _valid_macros(),
                        "calories": 9999,
                    }
                ],
            }
        )

        assert response.emoji == "🍜"
        assert response.items[0].quantity == pytest.approx(1.0)
        assert response.items[0].unit == "bowl"
        assert response.items[0].quantity_g == pytest.approx(550.0)
        assert "calories" not in response.model_dump()["items"][0]

    def test_accepts_missing_quantity_g_for_display_only_items(self):
        response = MealTextNutritionResponse.model_validate(
            {
                "items": [
                    {
                        "name": "Egg",
                        "quantity": 2.0,
                        "unit": "piece",
                        "macros": _valid_macros(),
                    }
                ]
            }
        )

        assert response.items[0].quantity_g is None

    def test_folds_current_flat_macro_shape_into_canonical_macros(self):
        response = MealTextNutritionResponse.model_validate(
            {
                "items": [
                    {
                        "name": "Eggs",
                        "quantity": 2.0,
                        "unit": "large",
                        "english_unit": "large",
                        "protein": 12.6,
                        "carbs": 0.7,
                        "fat": 9.5,
                        "calories": 144,
                    }
                ]
            }
        )

        item = response.items[0]
        assert item.macros.protein_g == pytest.approx(12.6)
        assert item.macros.carbs_g == pytest.approx(0.7)
        assert item.macros.fat_g == pytest.approx(9.5)
        assert "protein" not in item.model_dump()
        assert "calories" not in item.model_dump()

    def test_rejects_empty_items(self):
        with pytest.raises(ValidationError):
            MealTextNutritionResponse.model_validate({"items": []})

    def test_rejects_malformed_items(self):
        with pytest.raises(ValidationError):
            MealTextNutritionResponse.model_validate({"items": {"name": "Pho"}})
