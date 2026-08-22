"""
Handler for adding custom ingredients to meals.
"""

import logging
from typing import Any

from src.app.commands.meal import AddCustomIngredientCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.meal.food_item_change import FoodItemChange
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.services.meal_service import MealService
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(
    EventHandler[AddCustomIngredientCommand, dict[str, Any]]
):
    """Handler for adding custom ingredients to meals."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, command: AddCustomIngredientCommand) -> dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        try:
            async with self.uow as uow:
                meal = await uow.meals.find_by_id(command.meal_id)
                if not meal:
                    raise ValueError(f"Meal {command.meal_id} not found")

                change = FoodItemChange(
                    action="add",
                    name=command.name,
                    quantity=command.quantity,
                    unit=command.unit,
                    custom_nutrition=command.nutrition,
                )

                meal_service = MealService()
                updated_meal = meal_service.apply_food_item_changes(meal, [change])
                saved_meal = await uow.meals.save(updated_meal)

            meal_date = (saved_meal.created_at or utc_now()).date()
            if self.cache_invalidation:
                await self.cache_invalidation.after_meal_write(saved_meal.user_id, meal_date)

            return {
                "success": True,
                "meal_id": saved_meal.meal_id,
                "message": f"Added custom ingredient: {command.name}",
            }
        except Exception as e:
            raise
