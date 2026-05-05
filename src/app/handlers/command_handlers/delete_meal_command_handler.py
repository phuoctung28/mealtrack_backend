"""
Handler for hard-deleting meals with preservation of food item data.

This handler delegates the actual deletion logic to the meal repository,
which performs soft-deletes on translations/food items and hard-deletes
on nutrition/meal records.
"""

import logging
from typing import Any, Dict

from src.api.exceptions import ResourceNotFoundException, AuthorizationException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for hard-deleting a meal with data preservation."""

    def __init__(self, uow: UnitOfWorkPort, event_bus: Any):
        self.uow = uow
        self.event_bus = event_bus

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        """Handle meal deletion with data preservation."""
        async with self.uow as uow:
            meal = await uow.meals.find_by_id(command.meal_id)
            if not meal:
                raise ResourceNotFoundException(
                    f"Meal with ID {command.meal_id} not found"
                )

            if meal.user_id != command.user_id:
                raise AuthorizationException(
                    "You do not have permission to delete this meal"
                )

            await uow.meals.delete(command.meal_id)

        meal_date = (meal.created_at or utc_now()).date()
        await self.event_bus.publish(
            MealCacheInvalidationRequiredEvent(
                aggregate_id=command.user_id,
                user_id=command.user_id,
                meal_date=meal_date,
            )
        )

        return {
            "meal_id": command.meal_id,
            "message": "Meal deleted, ingredient data preserved",
        }
