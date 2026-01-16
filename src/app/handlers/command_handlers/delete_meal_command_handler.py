"""
Handler for soft-deleting meals (marking as INACTIVE).
"""
import logging
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for soft-deleting a meal (marking as INACTIVE)."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: DeleteMealCommand) -> Dict[str, Any]:
        """Handle meal deletion by marking as INACTIVE."""
        # Use provided UoW or create default
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                # Get meal
                meal = uow.meals.find_by_id(command.meal_id)
                if not meal:
                    raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")

                # Mark as inactive
                inactive_meal = meal.mark_inactive()
                uow.meals.save(inactive_meal)
                uow.commit()
                
                await self._invalidate_daily_macros(meal)

                return {
                    "meal_id": inactive_meal.meal_id,
                    "status": inactive_meal.status.value,
                    "message": "Meal marked as inactive"
                }
            except Exception as e:
                uow.rollback()
                logger.error(f"Error deleting meal: {str(e)}")
                raise

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or utc_now()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
