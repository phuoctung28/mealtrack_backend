"""
GetDailyMacrosQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import date
from typing import Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetDailyMacrosQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


@handles(GetDailyMacrosQuery)
class GetDailyMacrosQueryHandler(EventHandler[GetDailyMacrosQuery, Dict[str, Any]]):
    """Handler for calculating daily macronutrient totals with user targets."""

    def __init__(
        self,
        meal_repository: MealRepositoryPort = None,
        db=None,
        cache_service: Optional[CacheService] = None,
    ):
        self.meal_repository = meal_repository
        self.db = db
        self.cache_service = cache_service

    def set_dependencies(self, meal_repository: MealRepositoryPort, db=None, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository
        if db:
            self.db = db
        self.cache_service = kwargs.get("cache_service", self.cache_service)

    async def handle(self, query: GetDailyMacrosQuery) -> Dict[str, Any]:
        """Calculate daily macros for a given date with user targets."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")

        target_date = query.target_date or date.today()
        cached_result = await self._try_get_cached_result(query.user_id, target_date)
        if cached_result is not None:
            return cached_result

        meals = self.meal_repository.find_by_date(target_date, user_id=query.user_id)

        # Initialize totals
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        meal_count = 0
        meals_with_nutrition = 0

        # Calculate totals from meals with nutrition data
        for meal in meals:
            # Skip INACTIVE meals entirely
            if meal.status == MealStatus.INACTIVE:
                continue
            meal_count += 1
            if meal.nutrition and meal.status in [MealStatus.READY, MealStatus.ENRICHING]:
                meals_with_nutrition += 1
                total_calories += meal.nutrition.calories or 0
                if meal.nutrition.macros:
                    total_protein += meal.nutrition.macros.protein or 0
                    total_carbs += meal.nutrition.macros.carbs or 0
                    total_fat += meal.nutrition.macros.fat or 0

        # Get user's TDEE targets
        target_calories = None
        target_macros = None

        try:
            # Get TDEE calculation for the user
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
            from src.app.queries.tdee import GetUserTdeeQuery

            tdee_handler = GetUserTdeeQueryHandler(self.db)
            tdee_query = GetUserTdeeQuery(user_id=query.user_id)
            tdee_result = await tdee_handler.handle(tdee_query)

            target_calories = tdee_result.get('target_calories')
            target_macros = tdee_result.get('macros', {})
            
            if target_calories is None:
                logger.warning(f"TDEE data missing for user {query.user_id}. User may not have completed onboarding.")
        except Exception as e:
            logger.warning(f"Could not fetch TDEE data for user {query.user_id}: {e}", exc_info=True)
            # Continue without target data - mapper will handle this appropriately

        result = {
            "date": target_date.isoformat(),
            "user_id": query.user_id,
            "total_calories": round(total_calories, 1),
            "total_protein": round(total_protein, 1),
            "total_carbs": round(total_carbs, 1),
            "total_fat": round(total_fat, 1),
            "meal_count": meal_count,
            "meals_with_nutrition": meals_with_nutrition
        }

        # Add target data if available
        if target_calories is not None:
            result["target_calories"] = target_calories

        if target_macros:
            result["target_macros"] = {
                "protein": target_macros.get('protein', 0.0),
                "carbs": target_macros.get('carbs', 0.0),
                "fat": target_macros.get('fat', 0.0),
                "calories": target_macros.get('calories', target_calories or 0.0)
            }

        await self._write_cache(query.user_id, target_date, result)
        return result

    async def _try_get_cached_result(self, user_id: str, target_date: date):
        if not self.cache_service:
            return None
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        return await self.cache_service.get_json(cache_key)

    async def _write_cache(self, user_id: str, target_date: date, payload: Dict[str, Any]):
        if not self.cache_service:
            return
        cache_key, ttl = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.set_json(cache_key, payload, ttl)
