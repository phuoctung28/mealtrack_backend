"""
Handler for getting weekly macro budget status.
"""
import logging
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.model.meal import MealStatus
from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import ensure_utc, get_user_monday, get_zone_info, resolve_user_timezone
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetWeeklyBudgetQuery)
class GetWeeklyBudgetQueryHandler(EventHandler[GetWeeklyBudgetQuery, Dict[str, Any]]):
    """Handler for getting weekly macro budget status."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, query: GetWeeklyBudgetQuery) -> Dict[str, Any]:
        """Handle getting weekly budget status."""
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                # Resolve user timezone (DB → X-Timezone header → UTC)
                user_tz_str = resolve_user_timezone(
                    query.user_id, uow, query.header_timezone
                )
                user_tz = get_zone_info(user_tz_str)

                # Default to today in USER's timezone (not server's UTC)
                if query.target_date:
                    target_date = query.target_date
                else:
                    target_date = datetime.now(user_tz).date()

                # Get Monday for user's timezone
                week_start = get_user_monday(target_date, query.user_id, uow)

                # Find or create weekly budget
                weekly_budget = uow.weekly_budgets.find_by_user_and_week(query.user_id, week_start)

                if not weekly_budget:
                    # Lazy init: create weekly budget
                    weekly_budget, bmr = await self._create_weekly_budget(uow, query.user_id, week_start, target_date)
                else:
                    # Check if targets are stale and sync if needed
                    weekly_budget, bmr = await self._sync_targets_if_stale(
                        uow, weekly_budget, query.user_id
                    )

                # Calculate consumed from meals this week and update budget object
                consumed = await self._calculate_weekly_consumed(
                    uow, query.user_id, week_start, user_timezone=user_tz_str
                )
                weekly_budget.consumed_calories = consumed["calories"]
                weekly_budget.consumed_protein = consumed["protein"]
                weekly_budget.consumed_carbs = consumed["carbs"]
                weekly_budget.consumed_fat = consumed["fat"]
                uow.weekly_budgets.update(weekly_budget)

                # Load cheat days for this week
                cheat_days = uow.cheat_days.find_by_user_and_date_range(
                    query.user_id, week_start, week_start + timedelta(days=6)
                )

                # Calculate remaining days (including today)
                remaining_days = WeeklyBudgetService.calculate_remaining_days(
                    week_start, target_date
                )

                # Calculate adjusted daily targets using only PREVIOUS days' consumption
                # Today's eating should not change today's target (lock at start of day)
                consumed_before_today = await self._calculate_weekly_consumed(
                    uow, query.user_id, week_start,
                    exclude_date=target_date, user_timezone=user_tz_str,
                )
                budget_for_adjustment = replace(
                    weekly_budget,
                    consumed_calories=consumed_before_today["calories"],
                    consumed_protein=consumed_before_today["protein"],
                    consumed_carbs=consumed_before_today["carbs"],
                    consumed_fat=consumed_before_today["fat"],
                )
                adjusted = WeeklyBudgetService.calculate_adjusted_daily(
                    budget_for_adjustment,
                    standard_daily_calories=weekly_budget.target_calories / 7,
                    standard_daily_carbs=weekly_budget.target_carbs / 7,
                    standard_daily_fat=weekly_budget.target_fat / 7,
                    standard_daily_protein=weekly_budget.target_protein / 7,
                    bmr=bmr,
                    remaining_days=remaining_days,
                )

                # Derive remaining calories from macros for consistency
                remaining_p = weekly_budget.remaining_protein
                remaining_c = weekly_budget.remaining_carbs
                remaining_f = weekly_budget.remaining_fat
                derived_remaining_cal = (remaining_p * 4) + (remaining_c * 4) + (remaining_f * 9)

                return {
                    "week_start_date": week_start.isoformat(),
                    "target_calories": weekly_budget.target_calories,
                    "target_protein": weekly_budget.target_protein,
                    "target_carbs": weekly_budget.target_carbs,
                    "target_fat": weekly_budget.target_fat,
                    "consumed_calories": weekly_budget.consumed_calories,
                    "consumed_protein": weekly_budget.consumed_protein,
                    "consumed_carbs": weekly_budget.consumed_carbs,
                    "consumed_fat": weekly_budget.consumed_fat,
                    "remaining_calories": round(derived_remaining_cal, 1),
                    "remaining_protein": weekly_budget.remaining_protein,
                    "remaining_carbs": weekly_budget.remaining_carbs,
                    "remaining_fat": weekly_budget.remaining_fat,
                    "adjusted_daily_calories": adjusted.calories,
                    "adjusted_daily_carbs": adjusted.carbs,
                    "adjusted_daily_fat": adjusted.fat,
                    "daily_protein": adjusted.protein,
                    "remaining_days": remaining_days,
                    "bmr_floor_active": adjusted.bmr_floor_active,
                    "cheat_days": [cd.date.isoformat() for cd in cheat_days],
                }

            except Exception as e:
                logger.error(f"Error getting weekly budget: {str(e)}")
                raise

    async def _create_weekly_budget(
        self,
        uow: UnitOfWork,
        user_id: str,
        week_start: date,
        target_date: date
    ) -> tuple[WeeklyMacroBudget, float]:
        """Create a new weekly budget for the user. Returns (budget, bmr)."""
        from src.infra.database.models.weekly import WeeklyMacroBudget as DBWeeklyMacroBudget
        import uuid

        # Get user profile to find fitness goal
        profile = uow.users.get_profile(user_id)
        fitness_goal = profile.fitness_goal if profile else "cut"

        # Get TDEE-based macros using GetUserTdeeQueryHandler (correct pattern)
        target_calories = None
        daily_macros = {}
        bmr = 1800  # Default fallback

        try:
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
            from src.app.queries.tdee import GetUserTdeeQuery

            tdee_handler = GetUserTdeeQueryHandler()
            tdee_query = GetUserTdeeQuery(user_id=user_id)
            tdee_result = await tdee_handler.handle(tdee_query)

            daily_calories = tdee_result.get('target_calories', 2000)
            daily_macros = tdee_result.get('macros', {})
            bmr = tdee_result.get('bmr', 1800)

            target_calories = daily_calories * 7
            target_protein = daily_macros.get('protein', 70) * 7
            target_carbs = daily_macros.get('carbs', 200) * 7
            target_fat = daily_macros.get('fat', 70) * 7
        except Exception as e:
            # Fallback to defaults if TDEE calculation fails
            logger.warning(f"TDEE calc failed for user {user_id}, using defaults: {e}")
            target_calories = 14000  # 2000 * 7
            target_protein = 490  # 70 * 7
            target_carbs = 1400  # 200 * 7
            target_fat = 490  # 70 * 7

        # Create domain object
        budget = WeeklyMacroBudget(
            weekly_budget_id=str(uuid.uuid4()),
            user_id=user_id,
            week_start_date=week_start,
            target_calories=target_calories,
            target_protein=target_protein,
            target_carbs=target_carbs,
            target_fat=target_fat,
        )

        # Save to DB
        db_budget = DBWeeklyMacroBudget.from_domain(budget)
        uow.weekly_budgets.create(budget)

        return budget, bmr

    async def _calculate_weekly_consumed(
        self,
        uow: UnitOfWork,
        user_id: str,
        week_start: date,
        exclude_date: Optional[date] = None,
        user_timezone: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate consumed macros from meals this week.

        Args:
            exclude_date: If set, skip meals on this user-local date
                (used to lock today's target).
            user_timezone: IANA timezone for correct date boundary conversion.
        """
        week_end = week_start + timedelta(days=6)
        tz = get_zone_info(user_timezone) if user_timezone else None

        meals = uow.meals.find_by_date_range(
            user_id, week_start, week_end, user_timezone=user_timezone,
        )

        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        for meal in meals:
            if meal.status == MealStatus.READY and meal.nutrition:
                # Skip meals on excluded date (locks today's adjusted target)
                # Convert meal UTC timestamp to user-local date for comparison
                if exclude_date and meal.created_at:
                    aware_dt = ensure_utc(meal.created_at)
                    meal_local_date = (
                        aware_dt.astimezone(tz).date() if tz
                        else aware_dt.date()
                    )
                    if meal_local_date == exclude_date:
                        continue
                total_calories += meal.nutrition.calories or 0
                total_protein += meal.nutrition.macros.protein or 0
                total_carbs += meal.nutrition.macros.carbs or 0
                total_fat += meal.nutrition.macros.fat or 0

        return {
            "calories": total_calories,
            "protein": total_protein,
            "carbs": total_carbs,
            "fat": total_fat,
        }

    async def _sync_targets_if_stale(
        self,
        uow: UnitOfWork,
        weekly_budget: WeeklyMacroBudget,
        user_id: str
    ) -> tuple[WeeklyMacroBudget, float]:
        """Check if weekly targets match current TDEE; update if stale. Returns (budget, bmr)."""
        try:
            from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
            from src.app.queries.tdee import GetUserTdeeQuery

            tdee_handler = GetUserTdeeQueryHandler()
            tdee_result = await tdee_handler.handle(
                GetUserTdeeQuery(user_id=user_id)
            )

            daily_calories = tdee_result.get('target_calories')
            bmr = tdee_result.get('bmr', 1800)

            if daily_calories is None:
                return weekly_budget, bmr

            expected_weekly = round(daily_calories * 7, 1)
            current_weekly = round(weekly_budget.target_calories, 1)

            # Only update if >1% difference (avoid floating point noise)
            if abs(expected_weekly - current_weekly) / max(current_weekly, 1) > 0.01:
                daily_macros = tdee_result.get('macros', {})
                weekly_budget.target_calories = daily_calories * 7
                weekly_budget.target_protein = daily_macros.get('protein', 70) * 7
                weekly_budget.target_carbs = daily_macros.get('carbs', 200) * 7
                weekly_budget.target_fat = daily_macros.get('fat', 70) * 7
                uow.weekly_budgets.update(weekly_budget)
                logger.info(f"Updated stale weekly budget for user {user_id}: {current_weekly} → {expected_weekly}")

            return weekly_budget, bmr
        except Exception as e:
            logger.warning(f"Staleness check failed: {e}")
            return weekly_budget, 1800
