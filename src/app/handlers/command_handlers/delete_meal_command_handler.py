"""
Handler for soft-deleting meals (marking as INACTIVE).
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.meal import DeleteMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


@handles(DeleteMealCommand)
class DeleteMealCommandHandler(EventHandler[DeleteMealCommand, Dict[str, Any]]):
    """Handler for soft-deleting a meal (marking as INACTIVE)."""

    def __init__(self, meal_repository: MealRepositoryPort = None, cache_service: Optional[CacheService] = None):
        self.meal_repository = meal_repository
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.cache_service = kwargs.get('cache_service', self.cache_service)

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
        await self._invalidate_daily_macros(meal)

        return {
            "meal_id": inactive_meal.meal_id,
            "status": inactive_meal.status.value,
            "message": "Meal marked as inactive"
        }

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or datetime.utcnow()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
