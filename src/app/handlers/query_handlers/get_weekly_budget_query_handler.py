"""
Handler for getting weekly macro budget status.
"""
import logging
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.domain.constants import WeeklyBudgetConstants
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import get_user_monday, get_zone_info, resolve_user_timezone
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

                # Load cheat days for this week (pre-loaded, passed to shared method)
                cheat_days = uow.cheat_days.find_by_user_and_date_range(
                    query.user_id, week_start, week_start + timedelta(days=6)
                )
                past_cheat_dates = [cd.date for cd in cheat_days if cd.date < target_date]
                is_today_cheat = any(cd.date == target_date for cd in cheat_days)

                # Base daily targets
                base_daily_cal = weekly_budget.target_calories / 7
                base_daily_carbs = weekly_budget.target_carbs / 7
                base_daily_fat = weekly_budget.target_fat / 7
                base_daily_protein = weekly_budget.target_protein / 7

                # --- Skip & Redistribute via shared service ---
                effective = WeeklyBudgetService.get_effective_adjusted_daily(
                    uow=uow, user_id=query.user_id,
                    week_start=week_start, target_date=target_date,
                    weekly_budget=weekly_budget,
                    base_daily_cal=base_daily_cal,
                    base_daily_protein=base_daily_protein,
                    base_daily_carbs=base_daily_carbs,
                    base_daily_fat=base_daily_fat,
                    bmr=bmr, user_timezone=user_tz_str,
                    cheat_dates=past_cheat_dates,
                )
                adjusted = effective.adjusted
                consumed_before_today = effective.consumed_before_today
                consumed = effective.consumed_total
                skipped_days = effective.skipped_days
                show_logging_prompt = effective.show_logging_prompt
                logged_past_days = effective.logged_past_days
                remaining_days = adjusted.remaining_days

                # Update budget consumed values in DB from fresh meal data
                weekly_budget.consumed_calories = consumed["calories"]
                weekly_budget.consumed_protein = consumed["protein"]
                weekly_budget.consumed_carbs = consumed["carbs"]
                weekly_budget.consumed_fat = consumed["fat"]
                uow.weekly_budgets.update(weekly_budget)

                # --- Tomorrow Preview ---
                # Shows real impact of today's consumption on tomorrow's target.
                preview_data: Dict[str, Any] = {}
                today_consumed_cal = consumed["calories"] - consumed_before_today["calories"]
                logger.info(
                    f"Preview check: remaining={remaining_days}, prompt={show_logging_prompt}, "
                    f"today_cal={today_consumed_cal:.0f}, base={base_daily_cal:.0f}, "
                    f"consumed_total={consumed['calories']:.0f}, consumed_before={consumed_before_today['calories']:.0f}, "
                    f"logged_past={logged_past_days}, skipped={skipped_days}, "
                    f"cheat_today={is_today_cheat}, cheat_past={len(past_cheat_dates)}"
                )
                if remaining_days > 1 and not show_logging_prompt and today_consumed_cal > 0:
                    # Preview uses original consumed data (cheat days included) for real impact
                    tomorrow_remaining = remaining_days - 1
                    consumed_including_today = consumed.copy()
                    effective_days_tomorrow = logged_past_days + 1 + tomorrow_remaining  # +1 = today
                    prorated_tomorrow_cal = base_daily_cal * effective_days_tomorrow
                    prorated_tomorrow_carbs = base_daily_carbs * effective_days_tomorrow
                    prorated_tomorrow_fat = base_daily_fat * effective_days_tomorrow
                    prorated_tomorrow_protein = base_daily_protein * effective_days_tomorrow

                    tomorrow_budget = replace(
                        weekly_budget,
                        target_calories=prorated_tomorrow_cal,
                        target_protein=prorated_tomorrow_protein,
                        target_carbs=prorated_tomorrow_carbs,
                        target_fat=prorated_tomorrow_fat,
                        consumed_calories=consumed_including_today["calories"],
                        consumed_protein=consumed_including_today["protein"],
                        consumed_carbs=consumed_including_today["carbs"],
                        consumed_fat=consumed_including_today["fat"],
                    )
                    tomorrow_adjusted = WeeklyBudgetService.calculate_adjusted_daily(
                        tomorrow_budget,
                        standard_daily_calories=base_daily_cal,
                        standard_daily_carbs=base_daily_carbs,
                        standard_daily_fat=base_daily_fat,
                        standard_daily_protein=base_daily_protein,
                        bmr=bmr,
                        remaining_days=tomorrow_remaining,
                    )

                    deviation = abs(tomorrow_adjusted.calories - base_daily_cal) / max(base_daily_cal, 1)
                    logger.info(
                        f"Preview deviation: {deviation:.4f} (threshold={WeeklyBudgetConstants.PREVIEW_DEVIATION_THRESHOLD}), "
                        f"tomorrow_cal={tomorrow_adjusted.calories:.1f}, effective_days={effective_days_tomorrow}"
                    )
                    if deviation >= WeeklyBudgetConstants.PREVIEW_DEVIATION_THRESHOLD:
                        # Delta relative to today's adjusted target (what user sees on screen)
                        direction = "over" if today_consumed_cal > adjusted.calories else "under"
                        preview_data = {
                            "preview_tomorrow_calories": tomorrow_adjusted.calories,
                            "preview_tomorrow_protein": tomorrow_adjusted.protein,
                            "preview_tomorrow_carbs": tomorrow_adjusted.carbs,
                            "preview_tomorrow_fat": tomorrow_adjusted.fat,
                            "preview_direction": direction,
                            "preview_delta": int(abs(tomorrow_adjusted.calories - adjusted.calories)),
                            "preview_today_delta": int(abs(today_consumed_cal - adjusted.calories)),
                        }

                # Derive remaining calories directly from target - consumed (negatives flow through)
                derived_remaining_cal = weekly_budget.target_calories - weekly_budget.consumed_calories

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
                    "skipped_days": skipped_days,
                    "show_logging_prompt": show_logging_prompt,
                    **preview_data,
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
