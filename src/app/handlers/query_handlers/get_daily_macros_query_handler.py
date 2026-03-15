"""
GetDailyMacrosQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.meal import GetDailyMacrosQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition.macros import Macros
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import get_user_monday
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetDailyMacrosQuery)
class GetDailyMacrosQueryHandler(EventHandler[GetDailyMacrosQuery, Dict[str, Any]]):
    """Handler for calculating daily macronutrient totals with user targets."""

    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
    ):
        self.cache_service = cache_service

    async def handle(self, query: GetDailyMacrosQuery) -> Dict[str, Any]:
        """Calculate daily macros for a given date with user targets."""
        target_date = query.target_date or date.today()
        cached_result = await self._try_get_cached_result(query.user_id, target_date)
        if cached_result is not None:
            return cached_result

        # Use fresh UnitOfWork to get current data
        with UnitOfWork() as uow:
            meals = uow.meals.find_by_date(target_date, user_id=query.user_id)

            # Initialize totals
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            total_fiber = 0.0
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
                    if meal.nutrition.macros:
                        total_protein += meal.nutrition.macros.protein or 0
                        total_carbs += meal.nutrition.macros.carbs or 0
                        total_fat += meal.nutrition.macros.fat or 0
                        total_fiber += meal.nutrition.macros.fiber or 0

            # Derive total calories using fiber-aware formula — single source of truth
            total_calories = Macros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat,
                fiber=total_fiber,
            ).total_calories

        # Get user's TDEE targets
        target_calories = None
        target_macros = None

        try:
            # Get TDEE calculation for the user
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
            from src.app.queries.tdee import GetUserTdeeQuery

            tdee_handler = GetUserTdeeQueryHandler()
            tdee_query = GetUserTdeeQuery(user_id=query.user_id)
            tdee_result = await tdee_handler.handle(tdee_query)

            target_calories = tdee_result.get('target_calories')
            target_macros = tdee_result.get('macros', {})
            bmr = tdee_result.get('bmr', 1800)

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

        # Add weekly context if target calories available
        if target_calories:
            weekly_context = await self._get_weekly_context(
                query.user_id,
                target_date,
                target_calories,
                target_macros,
                total_calories,
                bmr,
            )
            if weekly_context:
                result["weekly_context"] = weekly_context

        await self._write_cache(query.user_id, target_date, result)
        return result

    async def _get_weekly_context(
        self,
        user_id: str,
        target_date: date,
        target_calories: float,
        target_macros: Dict,
        daily_consumed: float,
        bmr: float = 1800,
    ) -> Optional[Dict[str, Any]]:
        """Get weekly budget context for the daily macros response."""
        try:
            with UnitOfWork() as uow:
                # Get user's week start
                week_start = get_user_monday(target_date, user_id, uow)

                # Find or create weekly budget
                weekly_budget = uow.weekly_budgets.find_by_user_and_week(user_id, week_start)

                if not weekly_budget:
                    return None

                # Calculate remaining days in week
                remaining_days = WeeklyBudgetService.calculate_remaining_days(week_start, target_date)

                # Get standard daily targets
                standard_daily_calories = target_calories
                standard_daily_protein = target_macros.get('protein', 70) if target_macros else 70
                standard_daily_carbs = target_macros.get('carbs', 200) if target_macros else 200
                standard_daily_fat = target_macros.get('fat', 70) if target_macros else 70

                # Calculate adjusted daily targets
                adjusted = WeeklyBudgetService.calculate_adjusted_daily(
                    weekly_budget,
                    standard_daily_calories,
                    standard_daily_carbs,
                    standard_daily_fat,
                    standard_daily_protein,
                    bmr=bmr,
                    remaining_days=remaining_days,
                )

                # Build weekly context
                weekly_context = {
                    "adjusted_target_calories": adjusted.calories,
                    "adjusted_target_carbs": adjusted.carbs,
                    "adjusted_target_fat": adjusted.fat,
                    "daily_protein": adjusted.protein,
                    "bmr_floor_active": adjusted.bmr_floor_active,
                    "remaining_days": remaining_days,
                }

                return weekly_context

        except Exception as e:
            logger.warning(f"Could not fetch weekly budget context: {e}")
            return None

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
