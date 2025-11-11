"""
Handler for adding custom ingredients to meals.
"""
import logging
from typing import Dict, Any

from src.app.commands.meal import AddCustomIngredientCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_service import MealService
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(EventHandler[AddCustomIngredientCommand, Dict[str, Any]]):
    """Handler for adding custom ingredients to meals."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
        self.meal_service = MealService(meal_repository) if meal_repository else None

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        if self.meal_repository:
            self.meal_service = MealService(self.meal_repository)

    async def handle(self, command: AddCustomIngredientCommand) -> Dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        if not self.meal_service:
            raise RuntimeError("Meal service not configured")
        
        updated_meal = self.meal_service.add_custom_ingredient(
            meal_id=command.meal_id,
            name=command.name,
            quantity=command.quantity,
            unit=command.unit,
            nutrition=command.nutrition
        )
        
        return {
            "success": True,
            "meal_id": updated_meal.id,
            "message": f"Added custom ingredient: {command.name}"
        }
