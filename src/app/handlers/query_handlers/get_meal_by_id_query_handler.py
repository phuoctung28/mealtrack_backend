"""
GetMealByIdQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetMealByIdQuery
from src.domain.model.meal import Meal
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler(EventHandler[GetMealByIdQuery, Meal]):
    """Handler for retrieving a meal by ID."""

    def __init__(self):
        pass

    async def handle(self, query: GetMealByIdQuery) -> Meal:
        """Get meal by ID."""
        # Use fresh UnitOfWork to get current data
        with UnitOfWork() as uow:
            meal = uow.meals.find_by_id(query.meal_id)

            if not meal:
                raise ResourceNotFoundException(f"Meal with ID {query.meal_id} not found")

            return meal
