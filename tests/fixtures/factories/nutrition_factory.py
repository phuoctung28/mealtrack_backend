"""
Factory for creating test nutrition data.
"""
from uuid import uuid4
from typing import Optional, List, Dict, Any

from src.domain.model.nutrition.nutrition import Nutrition, FoodItem, Macros


class NutritionFactory:
    """Factory for nutrition data."""

    @staticmethod
    def create_nutrition(**overrides) -> Nutrition:
        """
        Create nutrition with realistic macros.

        Args:
            **overrides: Override any default nutrition attributes

        Returns:
            Nutrition: Domain nutrition model
        """
        # Remove any stale calories= kwarg so callers don't break
        overrides.pop("calories", None)
        defaults = {
            "macros": Macros(
                protein=30.0,
                carbs=50.0,
                fat=15.0
            ),
            "food_items": [
                NutritionFactory.create_food_item(
                    name="Chicken Breast",
                    quantity=150,
                    unit="g",
                ),
                NutritionFactory.create_food_item(
                    name="Rice",
                    quantity=100,
                    unit="g",
                ),
            ],
            "micros": None,
        }
        defaults.update(overrides)

        return Nutrition(**defaults)

    @staticmethod
    def create_food_item(**overrides) -> FoodItem:
        """
        Create a food item with nutrition.

        Args:
            **overrides: Override any default food item attributes

        Returns:
            FoodItem: Domain food item model
        """
        # Remove stale calories= kwarg — calories are derived from macros
        overrides.pop("calories", None)
        defaults = {
            "id": str(uuid4()),
            "name": "Test Food",
            "quantity": 100.0,
            "unit": "g",
            "macros": Macros(
                protein=10.0,
                carbs=15.0,
                fat=5.0
            ),
            "micros": None,
            "confidence": 0.95,
        }
        defaults.update(overrides)

        return FoodItem(**defaults)
