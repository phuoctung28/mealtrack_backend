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
from src.domain.model.meal_projection import MealProjection

logger = logging.getLogger(__name__)

MAX_DATE_RANGE = 60


@handles(GetNutritionBulkQuery)
class GetNutritionBulkQueryHandler(EventHandler[GetNutritionBulkQuery, Dict[str, Any]]):
    """Handler for bulk nutrition data retrieval."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetNutritionBulkQuery) -> Dict[str, Any]:
        """Fetch nutrition summaries for all dates in range (cache-aside).

        The full response is cached under a short-TTL per-range key. The short
        TTL bounds staleness from day-rollover (the weekly summary is relative
        to "today") and from rare target changes not on the high-frequency
        write paths; meal/movement/hydration/custom-macro writes purge this key
        synchronously (CacheInvalidationService) for instant freshness.
        """
        if (query.end_date - query.start_date).days > MAX_DATE_RANGE:
            raise ValueError(f"Date range cannot exceed {MAX_DATE_RANGE} days")

        if self.cache_service is None:
            return await self._compute(query)

        key, ttl = CacheKeys.nutrition_bulk(
            query.user_id, query.start_date, query.end_date
        )
        cached_or_fresh = await self.cache_service.get_or_set(
            key, lambda: self._compute(query), ttl
        )
        if cached_or_fresh is not None:
            return cached_or_fresh
        # get_or_set returns None only if the factory did; _compute never does.
        return await self._compute(query)

    async def _compute(self, query: GetNutritionBulkQuery) -> Dict[str, Any]:
        """Build the bulk nutrition response (uncached)."""
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

            # Single query for the full range; bucket by local date in Python.
            movement_by_date: Dict[date, float] = {}
            try:
                overall_start, _ = self._local_day_utc_range(query.start_date, user_tz_str)
                _, overall_end = self._local_day_utc_range(query.end_date, user_tz_str)
                included = await uow.movement_entries.fetch_included_kcal_for_range(
                    query.user_id, overall_start, overall_end
                )
                for logged_at, kcal in included:
                    local_date = logged_at.astimezone(user_tz).date()
                    movement_by_date[local_date] = movement_by_date.get(local_date, 0.0) + kcal
            except Exception as exc:
                logger.warning("Failed to fetch bulk movement data: %s", exc)

            dates_result: Dict[str, Dict[str, Any]] = {}
            current = query.start_date
            while current <= query.end_date:
                day_meals = meals_by_date.get(current, [])
                dates_result[current.isoformat()] = self._build_date_summary(
                    day_meals, target_calories, target_macros,
                    movement_kcal=movement_by_date.get(current, 0.0),
                )
                current += timedelta(days=1)

            week_start = get_user_monday(today, query.user_id)
            weekly_budget = await uow.weekly_budgets.find_by_user_and_week(
                query.user_id, week_start
            )

            weekly_summary = None
            if weekly_budget:
                base_daily = target_calories or (weekly_budget.target_calories / 7)
                effective = await WeeklyBudgetService.get_effective_adjusted_daily_async(
                    uow=uow,
                    user_id=query.user_id,
                    week_start=week_start,
                    target_date=today,
                    weekly_budget=weekly_budget,
                    base_daily_cal=base_daily,
                    base_daily_protein=(target_macros or {}).get("protein", 70),
                    base_daily_carbs=(target_macros or {}).get("carbs", 200),
                    base_daily_fat=(target_macros or {}).get("fat", 70),
                    bmr=bmr,
                    user_timezone=user_tz_str,
                )
                adjusted = effective.adjusted
                consumed = effective.consumed_total
                weekly_summary = {
                    "week_start_date": week_start.isoformat(),
                    "target_calories": weekly_budget.target_calories,
                    "consumed_calories": round(consumed["calories"], 1),
                    "remaining_calories": round(
                        weekly_budget.target_calories - consumed["calories"], 1
                    ),
                    "adjusted_daily_calories": adjusted.calories,
                    "remaining_days": adjusted.remaining_days,
                }

            cache_version = self._compute_cache_version(dates_result, weekly_summary)

        return {
            "dates": dates_result,
            "weekly_budget": weekly_summary,
            "cache_version": cache_version,
        }

    def _local_day_utc_range(self, target: date, user_tz_str: str):
        from datetime import datetime, time, timezone
        tz = get_zone_info(user_tz_str)
        start_local = datetime.combine(target, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

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
        movement_kcal: float = 0.0,
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

        food_calories = Macros(
            protein=total_protein,
            carbs=total_carbs,
            fat=total_fat,
            fiber=total_fiber,
        ).total_calories
        net_calories = food_calories - movement_kcal

        target_cal = target_calories or 2000
        target_prot = (target_macros or {}).get("protein", 70)
        target_carb = (target_macros or {}).get("carbs", 200)
        target_fat_val = (target_macros or {}).get("fat", 70)

        return {
            "has_meals": meal_count > 0,
            "meal_count": meal_count,
            "food_calories": round(food_calories, 1),
            "movement_kcal_burned": round(movement_kcal, 1),
            "totals": {
                "consumed": {
                    "calories": round(net_calories, 1),
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
                    "calories": round(target_cal - net_calories, 1),
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
