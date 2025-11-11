"""
Handler for soft-deleting meals (marking as INACTIVE).
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for soft-deleting a meal (marking as INACTIVE)."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        """Handle meal deletion by marking as INACTIVE."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")

        # Mark as inactive
        inactive_meal = meal.mark_inactive()
        self.meal_repository.save(inactive_meal)

        return {
            "meal_id": inactive_meal.meal_id,
            "status": inactive_meal.status.value,
            "message": "Meal marked as inactive"
        }
