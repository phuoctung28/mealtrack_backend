"""
GetDailyBreakdownQueryHandler — 7-day macro breakdown (actual vs target).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.meal.get_daily_breakdown_query import GetDailyBreakdownQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition.macros import Macros
from src.domain.ports.cache_port import CachePort
from src.domain.utils.timezone_utils import (
    get_user_monday,
    get_zone_info,
    resolve_user_timezone,
)
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)


@handles(GetDailyBreakdownQuery)
class GetDailyBreakdownQueryHandler(
    EventHandler[GetDailyBreakdownQuery, Dict[str, Any]]
):
    """Handler for 7-day per-day macro breakdown with consumed vs target."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetDailyBreakdownQuery) -> Dict[str, Any]:
        """Return 7 DailyBreakdownEntry dicts for Mon–Sun of the requested week."""
        with UnitOfWork() as uow:
            user_tz_str = resolve_user_timezone(
                query.user_id, uow, query.header_timezone
            )
            user_tz = get_zone_info(user_tz_str)
            today = datetime.now(user_tz).date()

            if query.week_start:
                week_start = query.week_start
            else:
                week_start = get_user_monday(today, query.user_id, uow)

            cached = await self._try_get_cached_result(query.user_id, week_start)
            if cached is not None:
                return cached

            days = [week_start + timedelta(days=i) for i in range(7)]
            meals = uow.meals.find_by_date_range(
                user_id=query.user_id,
                start_date=week_start,
                end_date=week_start + timedelta(days=6),
                user_timezone=user_tz_str,
                projection=MealProjection.MACROS_ONLY,
            )

        base_daily_cal, base_daily_protein, base_daily_carbs, base_daily_fat = (
            await self._get_base_daily_targets(query.user_id)
        )

        meals_by_day: Dict[date, List[Any]] = {day: [] for day in days}
        for meal in meals:
            meal_day = self._local_meal_date(meal.created_at, user_tz)
            if meal_day in meals_by_day:
                meals_by_day[meal_day].append(meal)

        entries: List[Dict[str, Any]] = []
        for day in days:
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            total_fiber = 0.0
            meal_count = 0

            for meal in meals_by_day.get(day, []):
                if meal.status == MealStatus.INACTIVE:
                    continue
                meal_count += 1
                if meal.nutrition and meal.status in [
                    MealStatus.READY,
                    MealStatus.ENRICHING,
                ]:
                    if meal.nutrition.macros:
                        total_protein += meal.nutrition.macros.protein or 0.0
                        total_carbs += meal.nutrition.macros.carbs or 0.0
                        total_fat += meal.nutrition.macros.fat or 0.0
                        total_fiber += meal.nutrition.macros.fiber or 0.0

            total_calories = Macros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat,
                fiber=total_fiber,
            ).total_calories

            entries.append(
                {
                    "date": day.isoformat(),
                    "calories_consumed": round(total_calories, 1),
                    "calories_target": round(base_daily_cal, 1),
                    "protein_consumed": round(total_protein, 1),
                    "protein_target": round(base_daily_protein, 1),
                    "carbs_consumed": round(total_carbs, 1),
                    "carbs_target": round(base_daily_carbs, 1),
                    "fat_consumed": round(total_fat, 1),
                    "fat_target": round(base_daily_fat, 1),
                    "meal_count": meal_count,
                }
            )

        result = {
            "days": entries,
            "week_start": week_start.isoformat(),
        }
        await self._write_cache(query.user_id, week_start, result)
        return result

    def _local_meal_date(self, created_at: datetime, user_tz) -> date:
        """Return the user's local date for a meal timestamp."""
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at.astimezone(user_tz).date()

    async def _get_base_daily_targets(
        self, user_id: str
    ) -> tuple[float, float, float, float]:
        """Return (calories, protein, carbs, fat) base daily targets from TDEE."""
        try:
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import (
                GetUserTdeeQueryHandler,
            )
            from src.app.queries.tdee import GetUserTdeeQuery

            result = await GetUserTdeeQueryHandler().handle(
                GetUserTdeeQuery(user_id=user_id)
            )
            cal = result.get("target_calories", 2000.0)
            macros = result.get("macros", {})
            return (
                cal,
                macros.get("protein", 70.0),
                macros.get("carbs", 200.0),
                macros.get("fat", 70.0),
            )
        except Exception as e:
            logger.warning(f"Could not fetch TDEE targets for {user_id}: {e}")
            return 2000.0, 70.0, 200.0, 70.0

    async def _try_get_cached_result(self, user_id: str, week_start: date):
        if not self.cache_service:
            return None
        cache_key, _ = CacheKeys.daily_breakdown(user_id, week_start)
        return await self.cache_service.get_json(cache_key)

    async def _write_cache(
        self, user_id: str, week_start: date, payload: Dict[str, Any]
    ):
        if not self.cache_service:
            return
        cache_key, ttl = CacheKeys.daily_breakdown(user_id, week_start)
        await self.cache_service.set_json(cache_key, payload, ttl)
