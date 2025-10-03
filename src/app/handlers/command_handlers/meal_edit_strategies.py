"""
Strategy pattern for handling different food item change actions.
Each strategy encapsulates the logic for add, update, or remove operations.
"""
import logging
from typing import Dict

from src.domain.services import NutritionCalculationService

logger = logging.getLogger(__name__)

class FoodItemChangeStrategyFactory:
    """Factory for creating appropriate strategy based on action."""

    @staticmethod
    def create_strategies(
        nutrition_service: NutritionCalculationService,
        food_service=None
    ) -> Dict[str, FoodItemChangeStrategy]:
        """Create all available strategies."""
        return {
            "add": AddFoodItemStrategy(nutrition_service, food_service),
            "update": UpdateFoodItemStrategy(nutrition_service),
            "remove": RemoveFoodItemStrategy(nutrition_service)
        }
