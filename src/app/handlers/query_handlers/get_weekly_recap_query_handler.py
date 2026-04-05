"""
Handler for weekly performance recap — aggregates last week's data into a single response.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func

from src.app.events.base import EventHandler, handles
from src.app.queries.meal.get_weekly_recap_query import GetWeeklyRecapQuery
from src.api.schemas.response.weekly_recap_response import (
    DailyBreakdownItem,
    WeeklyRecapResponse,
)
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition.macros import Macros
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import get_zone_info, resolve_user_timezone
from src.infra.database.models.meal.meal import Meal as DBMeal
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetWeeklyRecapQuery)
class GetWeeklyRecapQueryHandler(EventHandler[GetWeeklyRecapQuery, WeeklyRecapResponse]):
    """Handler for getting weekly performance recap."""

    def __init__(self, uow: Optional[Any] = None):
        self.uow = uow

    async def handle(self, query: GetWeeklyRecapQuery) -> WeeklyRecapResponse:
        """Compose weekly recap from existing services and repositories."""
        # Fetch TDEE targets outside UoW (async)
        base_daily_cal, base_daily_protein, base_daily_carbs, base_daily_fat = (
            await self._get_base_daily_targets(query.user_id)
        )

        uow = self.uow or UnitOfWork()

        with uow:
            try:
                user_tz_str = resolve_user_timezone(
                    query.user_id, uow, query.header_timezone
                )
                user_tz = get_zone_info(user_tz_str)
                today = datetime.now(user_tz).date()

                # Resolve week start — default to PREVIOUS week's Monday
                if query.week_start:
                    week_start = query.week_start
                else:
                    current_monday = today - timedelta(days=today.weekday())
                    week_start = current_monday - timedelta(weeks=1)

                week_end = week_start + timedelta(days=6)

                # Look up weekly budget for that week (targets)
                weekly_budget = uow.weekly_budgets.find_by_user_and_week(
                    query.user_id, week_start
                )
                if not weekly_budget:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=404,
                        detail=f"No weekly budget found for week starting {week_start}",
                    )

                # Weekly targets
                total_cal_target = weekly_budget.target_calories
                total_protein_target = weekly_budget.target_protein
                total_carbs_target = weekly_budget.target_carbs
                total_fat_target = weekly_budget.target_fat

                # Consumed totals via service (all 7 days, no exclusions)
                consumed = WeeklyBudgetService.calculate_weekly_consumed(
                    uow=uow,
                    user_id=query.user_id,
                    week_start=week_start,
                    user_timezone=user_tz_str,
                )
                total_cal_consumed = consumed["calories"]
                total_protein_consumed = consumed["protein"]
                total_carbs_consumed = consumed["carbs"]
                total_fat_consumed = consumed["fat"]

                # Days tracked (days with ≥1 meal)
                daily_counts: Dict[date, int] = uow.meals.get_daily_meal_counts(
                    query.user_id, week_start, week_end,
                    user_timezone=user_tz_str,
                )
                days_tracked = len(daily_counts)

                # Cheat days this week
                cheat_days = uow.cheat_days.find_by_user_and_date_range(
                    query.user_id, week_start, week_end
                )
                cheat_day_count = len(cheat_days)

                # Week number — ordinal since user's first week
                week_number = self._compute_week_number(
                    uow, query.user_id, week_start
                )

                # Last activity date across any week (gap detection)
                last_activity_date = self._get_last_activity_date(
                    uow, query.user_id, user_tz_str
                )

                # Adherence percentages — NOT capped at 100
                calorie_adherence_pct = round(
                    (total_cal_consumed / total_cal_target * 100)
                    if total_cal_target > 0 else 0.0,
                    1,
                )
                protein_adherence_pct = round(
                    (total_protein_consumed / total_protein_target * 100)
                    if total_protein_target > 0 else 0.0,
                    1,
                )

                # Averages per tracked day
                avg_daily_calories = round(
                    total_cal_consumed / days_tracked if days_tracked > 0 else 0.0, 1
                )
                avg_daily_protein = round(
                    total_protein_consumed / days_tracked if days_tracked > 0 else 0.0, 1
                )

                # Per-day breakdown (7 entries)
                daily_breakdown = self._build_daily_breakdown(
                    uow=uow,
                    user_id=query.user_id,
                    week_start=week_start,
                    user_tz_str=user_tz_str,
                    daily_counts=daily_counts,
                    base_daily_cal=base_daily_cal,
                    base_daily_protein=base_daily_protein,
                    base_daily_carbs=base_daily_carbs,
                    base_daily_fat=base_daily_fat,
                )

                return WeeklyRecapResponse(
                    week_start_date=week_start.isoformat(),
                    week_end_date=week_end.isoformat(),
                    week_number=week_number,
                    is_first_week=(week_number == 1),
                    days_tracked=days_tracked,
                    days_in_week=7,
                    total_calories_consumed=round(total_cal_consumed, 1),
                    total_protein_consumed=round(total_protein_consumed, 1),
                    total_carbs_consumed=round(total_carbs_consumed, 1),
                    total_fat_consumed=round(total_fat_consumed, 1),
                    total_calories_target=round(total_cal_target, 1),
                    total_protein_target=round(total_protein_target, 1),
                    total_carbs_target=round(total_carbs_target, 1),
                    total_fat_target=round(total_fat_target, 1),
                    calorie_adherence_pct=calorie_adherence_pct,
                    protein_adherence_pct=protein_adherence_pct,
                    avg_daily_calories=avg_daily_calories,
                    avg_daily_protein=avg_daily_protein,
                    cheat_day_count=cheat_day_count,
                    last_activity_date=last_activity_date,
                    daily_breakdown=daily_breakdown,
                )

            except Exception as e:
                logger.error(f"Error getting weekly recap: {str(e)}")
                raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_week_number(self, uow: UnitOfWork, user_id: str, week_start: date) -> int:
        """Derive ordinal week number from user's account creation date.

        Formula: (week_start - user.created_at.date()) // 7 + 1
        Falls back to 1 if user not found or created_at is missing.
        """
        try:
            user = uow.users.find_by_id(UUID(user_id))
            if user and user.created_at:
                user_created_date = user.created_at.date()
                # Align to the Monday of the user's first week
                user_first_monday = user_created_date - timedelta(
                    days=user_created_date.weekday()
                )
                delta_days = (week_start - user_first_monday).days
                return max(1, delta_days // 7 + 1)
        except Exception as e:
            logger.warning(f"Could not compute week number for {user_id}: {e}")
        return 1

    def _get_last_activity_date(
        self, uow: UnitOfWork, user_id: str, user_tz_str: str
    ) -> Optional[str]:
        """Return ISO date string of the most recent meal in user's timezone, or None."""
        try:
            result = (
                uow.session.query(func.max(DBMeal.created_at))
                .filter(
                    DBMeal.user_id == user_id,
                    DBMeal.status != MealStatusEnum.INACTIVE,
                )
                .scalar()
            )
            if result:
                if isinstance(result, datetime):
                    # Convert UTC → user timezone before extracting date
                    from datetime import timezone as tz
                    user_tz = get_zone_info(user_tz_str)
                    return result.replace(tzinfo=tz.utc).astimezone(user_tz).date().isoformat()
                return str(result)[:10]
        except Exception as e:
            logger.warning(f"Could not get last activity date for {user_id}: {e}")
        return None

    def _build_daily_breakdown(
        self,
        uow: UnitOfWork,
        user_id: str,
        week_start: date,
        user_tz_str: str,
        daily_counts: Dict[date, int],
        base_daily_cal: float,
        base_daily_protein: float,
        base_daily_carbs: float,
        base_daily_fat: float,
    ) -> List[DailyBreakdownItem]:
        """Build per-day breakdown for the 7 days of the week."""
        entries: List[DailyBreakdownItem] = []

        for i in range(7):
            day = week_start + timedelta(days=i)
            meals = uow.meals.find_by_date(
                day, user_id=user_id, user_timezone=user_tz_str
            )

            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            total_fiber = 0.0

            for meal in meals:
                if meal.status == MealStatus.INACTIVE:
                    continue
                if meal.nutrition and meal.status in [MealStatus.READY, MealStatus.ENRICHING]:
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

            meal_count = daily_counts.get(day, 0)

            entries.append(
                DailyBreakdownItem(
                    date=day.isoformat(),
                    calories_consumed=round(total_calories, 1),
                    calories_target=round(base_daily_cal, 1),
                    protein_consumed=round(total_protein, 1),
                    protein_target=round(base_daily_protein, 1),
                    carbs_consumed=round(total_carbs, 1),
                    carbs_target=round(base_daily_carbs, 1),
                    fat_consumed=round(total_fat, 1),
                    fat_target=round(base_daily_fat, 1),
                    meal_count=meal_count,
                )
            )

        return entries

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
