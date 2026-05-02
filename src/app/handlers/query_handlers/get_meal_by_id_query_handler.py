"""
GetMealByIdQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""

import logging

from src.api.exceptions import ResourceNotFoundException, AuthorizationException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetMealByIdQuery
from src.domain.model.meal import Meal
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)


@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler(EventHandler[GetMealByIdQuery, Meal]):
    """Handler for retrieving a meal by ID."""

    def __init__(self):
        pass

    async def handle(self, query: GetMealByIdQuery) -> Meal:
        """Get meal by ID."""
        # Use fresh AsyncUnitOfWork to get current data
        async with AsyncUnitOfWork() as uow:
            meal = await uow.meals.find_by_id(
                query.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS
            )

            if not meal:
                raise ResourceNotFoundException(
                    f"Meal with ID {query.meal_id} not found"
                )

            # Check ownership if user_id provided
            if query.user_id and meal.user_id != query.user_id:
                raise AuthorizationException(
                    "You do not have permission to access this meal"
                )

            return meal
