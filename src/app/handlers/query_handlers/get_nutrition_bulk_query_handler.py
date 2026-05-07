"""
Handler for bulk nutrition query - returns date-indexed summaries for a range.
"""
import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.nutrition import GetNutritionBulkQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition.macros import Macros
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import get_user_monday, get_zone_info, resolve_user_timezone_async
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)

MAX_DATE_RANGE = 60


@handles(GetNutritionBulkQuery)
class GetNutritionBulkQueryHandler(EventHandler[GetNutritionBulkQuery, Dict[str, Any]]):
    """Handler for bulk nutrition data retrieval."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetNutritionBulkQuery) -> Dict[str, Any]:
        """Fetch nutrition summaries for all dates in range."""
        if (query.end_date - query.start_date).days > MAX_DATE_RANGE:
            raise ValueError(f"Date range cannot exceed {MAX_DATE_RANGE} days")

        async with AsyncUnitOfWork() as uow:
            user_tz_str = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )
            user_tz = get_zone_info(user_tz_str)
            today = datetime.now(user_tz).date()

            meals = await uow.meals.find_by_date_range(
                query.user_id,
                query.start_date,
                query.end_date,
                user_timezone=user_tz_str,
                projection=MealProjection.MACROS_ONLY,
            )

            target_calories, target_macros, bmr = await self._get_user_targets(query.user_id)

            meals_by_date: Dict[date, list] = {}
            for meal in meals:
                if meal.status == MealStatus.INACTIVE:
                    continue
                meal_date = self._get_meal_date(meal, user_tz_str)
                if meal_date:
                    meals_by_date.setdefault(meal_date, []).append(meal)

            dates_result: Dict[str, Dict[str, Any]] = {}
            current = query.start_date
            while current <= query.end_date:
                day_meals = meals_by_date.get(current, [])
                dates_result[current.isoformat()] = self._build_date_summary(
                    day_meals, target_calories, target_macros
                )
                current += timedelta(days=1)

            week_start = get_user_monday(today, query.user_id)
            weekly_budget = await uow.weekly_budgets.find_by_user_and_week(
                query.user_id, week_start
            )

            weekly_summary = None
            if weekly_budget:
                remaining_days = WeeklyBudgetService.calculate_remaining_days(week_start, today)
                base_daily = target_calories or (weekly_budget.target_calories / 7)
                adjusted = WeeklyBudgetService.calculate_adjusted_daily(
                    weekly_budget,
                    standard_daily_calories=base_daily,
                    standard_daily_carbs=(target_macros or {}).get("carbs", 200),
                    standard_daily_fat=(target_macros or {}).get("fat", 70),
                    standard_daily_protein=(target_macros or {}).get("protein", 70),
                    bmr=bmr,
                    remaining_days=remaining_days,
                )
                weekly_summary = {
                    "week_start_date": week_start.isoformat(),
                    "target_calories": weekly_budget.target_calories,
                    "consumed_calories": weekly_budget.consumed_calories,
                    "remaining_calories": round(
                        weekly_budget.target_calories - weekly_budget.consumed_calories, 1
                    ),
                    "adjusted_daily_calories": adjusted.calories,
                    "remaining_days": remaining_days,
                }

            cache_version = self._compute_cache_version(dates_result, weekly_summary)

        return {
            "dates": dates_result,
            "weekly_budget": weekly_summary,
            "cache_version": cache_version,
        }

    def _get_meal_date(self, meal, user_tz_str: str) -> Optional[date]:
        """Extract local date from meal's created_at timestamp."""
        if not meal.created_at:
            return None
        tz = get_zone_info(user_tz_str)
        from src.domain.utils.timezone_utils import ensure_utc
        aware_dt = ensure_utc(meal.created_at)
        return aware_dt.astimezone(tz).date()

    def _build_date_summary(
        self,
        meals: list,
        target_calories: Optional[float],
        target_macros: Optional[Dict],
    ) -> Dict[str, Any]:
        """Build summary for a single date."""
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        meal_count = 0

        for meal in meals:
            meal_count += 1
            if meal.nutrition and meal.status in [MealStatus.READY, MealStatus.ENRICHING]:
                if meal.nutrition.macros:
                    total_protein += meal.nutrition.macros.protein or 0
                    total_carbs += meal.nutrition.macros.carbs or 0
                    total_fat += meal.nutrition.macros.fat or 0
                    total_fiber += meal.nutrition.macros.fiber or 0

        total_calories = Macros(
            protein=total_protein,
            carbs=total_carbs,
            fat=total_fat,
            fiber=total_fiber,
        ).total_calories

        target_cal = target_calories or 2000
        target_prot = (target_macros or {}).get("protein", 70)
        target_carb = (target_macros or {}).get("carbs", 200)
        target_fat_val = (target_macros or {}).get("fat", 70)

        return {
            "has_meals": meal_count > 0,
            "meal_count": meal_count,
            "totals": {
                "consumed": {
                    "calories": round(total_calories, 1),
                    "protein": round(total_protein, 1),
                    "carbs": round(total_carbs, 1),
                    "fat": round(total_fat, 1),
                },
                "target": {
                    "calories": round(target_cal, 1),
                    "protein": round(target_prot, 1),
                    "carbs": round(target_carb, 1),
                    "fat": round(target_fat_val, 1),
                },
                "remaining": {
                    "calories": round(target_cal - total_calories, 1),
                    "protein": round(target_prot - total_protein, 1),
                    "carbs": round(target_carb - total_carbs, 1),
                    "fat": round(target_fat_val - total_fat, 1),
                },
            },
        }

    async def _get_user_targets(self, user_id: str) -> tuple:
        """Get user's TDEE targets. Returns (target_calories, target_macros, bmr)."""
        try:
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
            from src.app.queries.tdee import GetUserTdeeQuery

            tdee_handler = GetUserTdeeQueryHandler(cache_service=self.cache_service)
            tdee_result = await tdee_handler.handle(GetUserTdeeQuery(user_id=user_id))
            return (
                tdee_result.get("target_calories"),
                tdee_result.get("macros", {}),
                tdee_result.get("bmr", 1800),
            )
        except Exception as e:
            logger.warning(f"Could not fetch TDEE for user {user_id}: {e}")
            return (None, None, 1800)

    def _compute_cache_version(
        self, dates: Dict[str, Any], weekly: Optional[Dict]
    ) -> str:
        """Compute a version hash for cache staleness detection."""
        import json
        content = json.dumps({"d": dates, "w": weekly}, sort_keys=True)
        return f"v1-{hashlib.md5(content.encode()).hexdigest()[:8]}"
