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
        defaults = {
            "calories": 500.0,
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
                    calories=247.5
                ),
                NutritionFactory.create_food_item(
                    name="Rice",
                    quantity=100,
                    unit="g",
                    calories=130.0
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
        defaults = {
            "id": str(uuid4()),
            "name": "Test Food",
            "quantity": 100.0,
            "unit": "g",
            "calories": 100.0,
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
