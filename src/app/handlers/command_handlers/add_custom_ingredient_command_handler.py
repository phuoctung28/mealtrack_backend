"""
Handler for adding custom ingredients to meals.
"""
import logging
from typing import Dict, Any, Optional

from src.app.commands.meal import AddCustomIngredientCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.services.meal_service import MealService
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(EventHandler[AddCustomIngredientCommand, Dict[str, Any]]):
    """Handler for adding custom ingredients to meals."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.uow = kwargs.get('uow', self.uow)
        self.cache_service = kwargs.get('cache_service', self.cache_service)

    async def handle(self, command: AddCustomIngredientCommand) -> Dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        # Use provided UoW or create default
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                meal_service = MealService(uow.meals)
                updated_meal = meal_service.add_custom_ingredient(
                    meal_id=command.meal_id,
                    name=command.name,
                    quantity=command.quantity,
                    unit=command.unit,
                    nutrition=command.nutrition
                )
                uow.commit()

                await self._invalidate_daily_macros(updated_meal)

                return {
                    "success": True,
                    "meal_id": updated_meal.meal_id,
                    "message": f"Added custom ingredient: {command.name}"
                }
            except Exception as e:
                uow.rollback()
                logger.error(f"Error adding custom ingredient: {str(e)}")
                raise

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or utc_now()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
