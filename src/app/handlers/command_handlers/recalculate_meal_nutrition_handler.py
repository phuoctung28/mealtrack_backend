"""
Handler for recalculating meal nutrition based on weight.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import RecalculateMealNutritionCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal import MealNutritionUpdatedEvent
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.services.pinecone_service import get_pinecone_service

logger = logging.getLogger(__name__)


@handles(RecalculateMealNutritionCommand)
class RecalculateMealNutritionCommandHandler(EventHandler[RecalculateMealNutritionCommand, Dict[str, Any]]):
    """Handler for recalculating meal nutrition based on weight."""

    def __init__(self, meal_repository: MealRepositoryPort = None, pinecone_service=None):
        self.meal_repository = meal_repository
        self.pinecone_service = pinecone_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.pinecone_service = kwargs.get('pinecone_service', self.pinecone_service)

    async def handle(self, command: RecalculateMealNutritionCommand) -> Dict[str, Any]:
        """Recalculate meal nutrition using Pinecone for fresh ingredient data."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        # Validate weight
        if command.weight_grams <= 0:
            raise ValidationException("Weight must be greater than 0")

        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")

        if not meal.nutrition or not meal.nutrition.food_items:
            raise ValidationException(f"Meal {command.meal_id} has no food items to recalculate")

        # Use Pinecone to recalculate nutrition for all ingredients
        try:
            # Use injected service, fallback to get_pinecone_service if not injected
            pinecone_svc = self.pinecone_service or get_pinecone_service()

            # Calculate total nutrition using Pinecone
            total_nutrition = pinecone_svc.calculate_total_nutrition([
                {
                    'name': item.name,
                    'quantity': item.quantity,
                    'unit': item.unit
                }
                for item in meal.nutrition.food_items
            ])

            # Update meal nutrition with Pinecone-calculated values
            meal.nutrition.calories = total_nutrition.calories
            meal.nutrition.macros.protein = total_nutrition.protein
            meal.nutrition.macros.carbs = total_nutrition.carbs
            meal.nutrition.macros.fat = total_nutrition.fat

        except Exception as e:
            logger.error(f"Error using Pinecone for recalculation: {e}")
            # Fall back to simple scaling if Pinecone fails
            old_weight = getattr(meal, 'weight_grams', 100.0)
            scale_factor = command.weight_grams / old_weight

            meal.nutrition.calories = meal.nutrition.calories * scale_factor
            meal.nutrition.macros.protein = meal.nutrition.macros.protein * scale_factor
            meal.nutrition.macros.carbs = meal.nutrition.macros.carbs * scale_factor
            meal.nutrition.macros.fat = meal.nutrition.macros.fat * scale_factor

        # Save updated meal
        updated_meal = self.meal_repository.save(meal)

        # Prepare nutrition data for response
        nutrition_data = {
            "calories": round(updated_meal.nutrition.calories, 1),
            "protein": round(updated_meal.nutrition.macros.protein, 1),
            "carbs": round(updated_meal.nutrition.macros.carbs, 1),
            "fat": round(updated_meal.nutrition.macros.fat, 1)
        }

        return {
            "meal_id": command.meal_id,
            "updated_nutrition": nutrition_data,
            "weight_grams": command.weight_grams,
            "events": [
                MealNutritionUpdatedEvent(
                    aggregate_id=command.meal_id,
                    meal_id=command.meal_id,
                    old_weight=getattr(meal, 'weight_grams', 100.0),
                    new_weight=command.weight_grams,
                    updated_nutrition=nutrition_data
                )
            ]
        }
