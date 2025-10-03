"""
Handler for adding custom ingredients to meals.
"""
import logging
from typing import Dict, Any

from src.app.commands.meal import AddCustomIngredientCommand, EditMealCommand, FoodItemChange
from src.app.events.base import EventHandler, handles
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(EventHandler[AddCustomIngredientCommand, Dict[str, Any]]):
    """Handler for adding custom ingredients to meals."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)

    async def handle(self, command: AddCustomIngredientCommand) -> Dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        # Delegate to EditMealCommand with custom ingredient
        from src.app.handlers.command_handlers.edit_meal_handler import EditMealCommandHandler

        edit_command = EditMealCommand(
            meal_id=command.meal_id,
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name=command.name,
                    quantity=command.quantity,
                    unit=command.unit,
                    custom_nutrition=command.nutrition
                )
            ]
        )

        # Use the edit handler
        edit_handler = EditMealCommandHandler(self.meal_repository)
        return await edit_handler.handle(edit_command)
