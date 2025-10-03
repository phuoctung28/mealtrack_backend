"""
GetMealByIdQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetMealByIdQuery
from src.domain.model.meal import Meal
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler(EventHandler[GetMealByIdQuery, Meal]):
    """Handler for retrieving a meal by ID."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository

    async def handle(self, query: GetMealByIdQuery) -> Meal:
        """Get meal by ID."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        meal = self.meal_repository.find_by_id(query.meal_id)

        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {query.meal_id} not found")

        return meal
