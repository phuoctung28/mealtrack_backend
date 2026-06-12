"""
Handler for hard-deleting meals with preservation of food item data.

This handler delegates the actual deletion logic to the meal repository,
which performs soft-deletes on translations/food items and hard-deletes
on nutrition/meal records.
"""

import logging
from typing import Any

from src.domain.exceptions.base import AuthorizationException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, dict[str, Any]]):
    """Handler for hard-deleting a meal with data preservation."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, command: DeleteMealCommand) -> dict[str, Any]:
        """Handle meal deletion with data preservation."""
        async with self.uow as uow:
            meal = await uow.meals.find_by_id(command.meal_id)
            if not meal:
                return {"meal_id": command.meal_id, "message": "Meal already deleted"}

            if meal.user_id != command.user_id:
                raise AuthorizationException(
                    "You do not have permission to delete this meal"
                )

            await uow.meals.delete(command.meal_id)

        meal_date = (meal.created_at or utc_now()).date()
        if self.cache_invalidation:
            await self.cache_invalidation.after_meal_write(command.user_id, meal_date)

        return {
            "meal_id": command.meal_id,
            "message": "Meal deleted, ingredient data preserved",
        }
