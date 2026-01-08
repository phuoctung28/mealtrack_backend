"""
Handler for adding custom ingredients to meals.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.app.commands.meal import AddCustomIngredientCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_service import MealService
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


@handles(AddCustomIngredientCommand)
class AddCustomIngredientCommandHandler(EventHandler[AddCustomIngredientCommand, Dict[str, Any]]):
    """Handler for adding custom ingredients to meals."""

    def __init__(self, meal_repository: MealRepositoryPort = None, cache_service: Optional[CacheService] = None):
        self.meal_repository = meal_repository
        self.meal_service = MealService(meal_repository) if meal_repository else None
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        if self.meal_repository:
            self.meal_service = MealService(self.meal_repository)
        self.cache_service = kwargs.get('cache_service', self.cache_service)

    async def handle(self, command: AddCustomIngredientCommand) -> Dict[str, Any]:
        """Handle adding custom ingredient to meal."""
        if not self.meal_service:
            raise RuntimeError("Meal service not configured")
        
        updated_meal = self.meal_service.add_custom_ingredient(
            meal_id=command.meal_id,
            name=command.name,
            quantity=command.quantity,
            unit=command.unit,
            nutrition=command.nutrition
        )
        
        await self._invalidate_daily_macros(updated_meal)

        return {
            "success": True,
            "meal_id": updated_meal.meal_id,
            "message": f"Added custom ingredient: {command.name}"
        }

    async def _invalidate_daily_macros(self, meal):
        if not self.cache_service or not meal:
            return
        created_at = meal.created_at or datetime.utcnow()
        cache_key, _ = CacheKeys.daily_macros(meal.user_id, created_at.date())
        await self.cache_service.invalidate(cache_key)
