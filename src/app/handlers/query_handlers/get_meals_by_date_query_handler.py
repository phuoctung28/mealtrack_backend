"""
GetMealsByDateQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import List

from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetMealsByDateQuery
from src.domain.model.meal import Meal
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetMealsByDateQuery)
class GetMealsByDateQueryHandler(EventHandler[GetMealsByDateQuery, List[Meal]]):
    """Handler for retrieving meals by date."""

    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository

    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository

    async def handle(self, query: GetMealsByDateQuery) -> List[Meal]:
        """Get meals for a specific date and user."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        return self.meal_repository.find_by_date(query.target_date, user_id=query.user_id)
