"""
Weekly budget service for redistribution logic and smart prompt detection.

Single source of truth for adjusted daily targets — used by:
- GetWeeklyBudgetQueryHandler (API)
- get_adjusted_daily_target (notification + suggestion)
"""
import logging
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.domain.constants import WeeklyBudgetConstants
from src.domain.model.meal import MealStatus
from src.domain.utils.timezone_utils import ensure_utc, get_zone_info

logger = logging.getLogger(__name__)


@dataclass
class AdjustedDailyTargets:
    """Adjusted daily targets based on weekly budget consumption."""
    calories: float
    carbs: float
    fat: float
    protein: float
    bmr_floor_active: bool
    remaining_days: int


@dataclass
class EffectiveAdjustedResult:
    """Rich result from get_effective_adjusted_daily with context for UI."""
    adjusted: AdjustedDailyTargets
    consumed_before_today: Dict[str, float]
    consumed_total: Dict[str, float]
    logged_past_days: int
    skipped_days: int
    show_logging_prompt: bool


class WeeklyBudgetService:
    """Service for weekly budget calculations."""

    @staticmethod
    def calculate_weekly_consumed(
        uow: Any,
        user_id: str,
        week_start: date,
        exclude_date: Optional[date] = None,
        exclude_dates: Optional[List[date]] = None,
        user_timezone: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate consumed macros from actual meals this week.

        Recalculates from meal records (not stale DB budget values).

        Args:
            uow: Unit of work with meals repository
            user_id: User ID
            week_start: Monday of the week
            exclude_date: Skip meals on this user-local date (today lock)
            exclude_dates: Skip meals on these user-local dates (cheat days)
            user_timezone: IANA timezone for correct date boundary
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

        exclude_dates_set = set(exclude_dates) if exclude_dates else set()
        for meal in meals:
            if meal.status == MealStatus.READY and meal.nutrition:
                # Skip meals on excluded dates (today lock + cheat days)
                if (exclude_date or exclude_dates_set) and meal.created_at:
                    aware_dt = ensure_utc(meal.created_at)
                    meal_local_date = (
                        aware_dt.astimezone(tz).date() if tz
                        else aware_dt.date()
                    )
                    if exclude_date and meal_local_date == exclude_date:
                        continue
                    if meal_local_date in exclude_dates_set:
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

    @staticmethod
    def get_effective_adjusted_daily(
        uow: Any,
        user_id: str,
        week_start: date,
        target_date: date,
        weekly_budget: Any,
        base_daily_cal: float,
        base_daily_protein: float,
        base_daily_carbs: float,
        base_daily_fat: float,
        bmr: float,
        user_timezone: str = "UTC",
        cheat_dates: Optional[List[date]] = None,
    ) -> EffectiveAdjustedResult:
        """Single source of truth for adjusted daily target with Skip & Redistribute.

        Recalculates consumed from actual meals, applies skip/redistribute logic,
        and returns rich result with context for UI callers.

        Args:
            uow: Unit of work with meals + cheat_days repos
            user_id: User ID
            week_start: Monday of the week
            target_date: The date to compute adjusted target for
            weekly_budget: WeeklyMacroBudget entity (pre-fetched by caller)
            base_daily_cal/protein/carbs/fat: Standard daily targets (weekly / 7)
            bmr: Basal metabolic rate for floor calculation
            user_timezone: IANA timezone string
            cheat_dates: Past cheat dates to exclude from redistribution.
                - Handler: passes pre-loaded past-only dates (avoids double query)
                - Notification/suggestion: passes None → auto-loads all-week dates,
                  then filters to past-only internally
        """
        calc = WeeklyBudgetService

        # --- Resolve cheat days ---
        if cheat_dates is None:
            cheat_day_records = uow.cheat_days.find_by_user_and_date_range(
                user_id, week_start, week_start + timedelta(days=6)
            )
            all_cheat_dates = [cd.date for cd in cheat_day_records]
        else:
            all_cheat_dates = cheat_dates

        past_cheat_dates = [d for d in all_cheat_dates if d < target_date]
        past_cheat_count = len(past_cheat_dates)

        # --- Remaining days ---
        remaining_days = calc.calculate_remaining_days(week_start, target_date)

        # --- Count logged past days ---
        past_end = target_date - timedelta(days=1)
        skipped_days = 0
        show_logging_prompt = False
        logged_past_days = 0

        past_days_count = (target_date - week_start).days
        if past_days_count > 0:
            daily_counts = uow.meals.get_daily_meal_counts(
                user_id, week_start, past_end,
                user_timezone=user_timezone,
            )
            logged_past_days = len(daily_counts)
            skipped_days = past_days_count - logged_past_days

            total_logged = logged_past_days + 1  # +1 for today
            if (total_logged < WeeklyBudgetConstants.MIN_LOGGED_DAYS_FOR_REDISTRIBUTION
                    and past_days_count >= 3):
                show_logging_prompt = True

        # Cheat days don't count as logged for redistribution
        redistribution_logged_days = max(0, logged_past_days - past_cheat_count)

        # --- Calculate consumed totals from actual meals ---
        consumed_total = calc.calculate_weekly_consumed(
            uow, user_id, week_start, user_timezone=user_timezone,
        )
        consumed_before_today = calc.calculate_weekly_consumed(
            uow, user_id, week_start,
            exclude_date=target_date, user_timezone=user_timezone,
        )

        # For redistribution: exclude cheat day consumption too
        if past_cheat_dates:
            consumed_for_redistribution = calc.calculate_weekly_consumed(
                uow, user_id, week_start,
                exclude_date=target_date,
                exclude_dates=past_cheat_dates,
                user_timezone=user_timezone,
            )
        else:
            consumed_for_redistribution = consumed_before_today

        # --- Calculate adjusted daily ---
        if show_logging_prompt:
            # Insufficient logging data → return base targets
            adjusted = calc.calculate_adjusted_daily(
                replace(weekly_budget, consumed_calories=0, consumed_protein=0,
                        consumed_carbs=0, consumed_fat=0),
                standard_daily_calories=base_daily_cal,
                standard_daily_carbs=base_daily_carbs,
                standard_daily_fat=base_daily_fat,
                standard_daily_protein=base_daily_protein,
                bmr=bmr, remaining_days=7,
            )
        else:
            # Skip & Redistribute: shrink effective week (excludes cheat days)
            effective_week_days = redistribution_logged_days + remaining_days
            prorated_target_cal = base_daily_cal * effective_week_days
            prorated_target_carbs = base_daily_carbs * effective_week_days
            prorated_target_fat = base_daily_fat * effective_week_days
            prorated_target_protein = base_daily_protein * effective_week_days

            budget_for_adjustment = replace(
                weekly_budget,
                target_calories=prorated_target_cal,
                target_protein=prorated_target_protein,
                target_carbs=prorated_target_carbs,
                target_fat=prorated_target_fat,
                consumed_calories=consumed_for_redistribution["calories"],
                consumed_protein=consumed_for_redistribution["protein"],
                consumed_carbs=consumed_for_redistribution["carbs"],
                consumed_fat=consumed_for_redistribution["fat"],
            )
            adjusted = calc.calculate_adjusted_daily(
                budget_for_adjustment,
                standard_daily_calories=base_daily_cal,
                standard_daily_carbs=base_daily_carbs,
                standard_daily_fat=base_daily_fat,
                standard_daily_protein=base_daily_protein,
                bmr=bmr,
                remaining_days=remaining_days,
            )

        # --- Budget cap: adjusted daily must not exceed actual remaining per day ---
        # Skip & Redistribute can inflate adjusted daily above what the real
        # remaining budget allows (e.g. cheat day consumption excluded from
        # redistribution but still counts toward weekly total). Cap to prevent
        # promising more than the budget can deliver.
        actual_remaining = weekly_budget.target_calories - consumed_total["calories"]
        if remaining_days > 0 and actual_remaining > 0:
            max_daily = actual_remaining / remaining_days
            if adjusted.calories > max_daily:
                scale = max_daily / adjusted.calories
                adjusted = AdjustedDailyTargets(
                    calories=round(max_daily, 1),
                    carbs=round(adjusted.carbs * scale, 1),
                    fat=round(adjusted.fat * scale, 1),
                    protein=adjusted.protein,  # protein stays fixed
                    bmr_floor_active=adjusted.bmr_floor_active,
                    remaining_days=adjusted.remaining_days,
                )

        return EffectiveAdjustedResult(
            adjusted=adjusted,
            consumed_before_today=consumed_before_today,
            consumed_total=consumed_total,
            logged_past_days=logged_past_days,
            skipped_days=skipped_days,
            show_logging_prompt=show_logging_prompt,
        )

    @staticmethod
    def calculate_adjusted_daily(
        weekly_budget: "WeeklyMacroBudget",
        standard_daily_calories: float,
        standard_daily_carbs: float,
        standard_daily_fat: float,
        standard_daily_protein: float,
        bmr: float,
        remaining_days: int,
    ) -> AdjustedDailyTargets:
        """Calculate adjusted daily targets based on remaining weekly budget.

        Pure math — no DB access. Uses budget's remaining_* properties.
        """
        if remaining_days <= 0:
            remaining_days = 1

        # Calculate BMR floor (80% of standard daily)
        bmr_floor = max(bmr, standard_daily_calories * WeeklyBudgetConstants.BMR_FLOOR_RATIO)

        # Redistribute remaining weekly budget
        remaining_calories = weekly_budget.remaining_calories
        remaining_carbs = weekly_budget.remaining_carbs
        remaining_fat = weekly_budget.remaining_fat

        adjusted_calories = remaining_calories / remaining_days
        adjusted_carbs = remaining_carbs / remaining_days
        adjusted_fat = remaining_fat / remaining_days

        # Apply floors and ceilings to macros (prevents 0g fat, absurd carbs)
        floor = WeeklyBudgetConstants.MACRO_FLOOR_RATIO
        ceil = WeeklyBudgetConstants.MACRO_CEILING_RATIO
        adjusted_carbs = max(standard_daily_carbs * floor,
                            min(adjusted_carbs, standard_daily_carbs * ceil))
        adjusted_fat = max(standard_daily_fat * floor,
                          min(adjusted_fat, standard_daily_fat * ceil))

        # Protein stays fixed regardless of weekly consumption
        adjusted_protein = standard_daily_protein

        # Round macros to 1 decimal first
        rounded_protein = round(adjusted_protein, 1)
        rounded_carbs = round(adjusted_carbs, 1)
        rounded_fat = round(adjusted_fat, 1)

        # Derive calories from rounded macros — single source of truth
        adjusted_calories = (rounded_protein * 4) + (rounded_carbs * 4) + (rounded_fat * 9)

        # Calorie cap: prevent macro inflation above calorie-level redistribution.
        # When user over-eats expensive macros (fat=9cal/g) but under-eats cheap
        # macros (carbs=4cal/g), independent macro redistribution can inflate
        # calories above what pure calorie redistribution would give.
        calorie_redistributed = remaining_calories / remaining_days
        if adjusted_calories > calorie_redistributed and calorie_redistributed < standard_daily_calories:
            protein_cal = rounded_protein * 4
            non_protein_target = calorie_redistributed - protein_cal
            non_protein_current = (rounded_carbs * 4) + (rounded_fat * 9)
            if non_protein_current > 0 and non_protein_target > 0:
                scale = non_protein_target / non_protein_current
                rounded_carbs = round(rounded_carbs * scale, 1)
                rounded_fat = round(rounded_fat * scale, 1)
                adjusted_calories = protein_cal + (rounded_carbs * 4) + (rounded_fat * 9)

        # Deficit cap: never reduce more than MAX_DAILY_DEFICIT_RATIO below base
        min_allowed = standard_daily_calories * (1 - WeeklyBudgetConstants.MAX_DAILY_DEFICIT_RATIO)
        if adjusted_calories < min_allowed:
            deficit_gap = min_allowed - adjusted_calories
            # Scale carbs and fat up proportionally to meet minimum
            carb_cal = rounded_carbs * 4
            fat_cal = rounded_fat * 9
            total_non_protein_cal = carb_cal + fat_cal
            if total_non_protein_cal > 0:
                carb_ratio = carb_cal / total_non_protein_cal
                fat_ratio = fat_cal / total_non_protein_cal
                rounded_carbs = round(rounded_carbs + (deficit_gap * carb_ratio) / 4, 1)
                rounded_fat = round(rounded_fat + (deficit_gap * fat_ratio) / 9, 1)
            # Re-derive calories from updated macros
            adjusted_calories = (rounded_protein * 4) + (rounded_carbs * 4) + (rounded_fat * 9)

        # Check if we hit the BMR floor
        bmr_floor_active = False
        if adjusted_calories < bmr_floor:
            adjusted_calories = bmr_floor
            bmr_floor_active = True

        return AdjustedDailyTargets(
            calories=round(adjusted_calories, 1),
            carbs=rounded_carbs,
            fat=rounded_fat,
            protein=rounded_protein,
            bmr_floor_active=bmr_floor_active,
            remaining_days=remaining_days,
        )

    @staticmethod
    def should_suggest_cheat_day(
        daily_consumed: float,
        daily_target: float,
        is_already_cheat_day: bool,
    ) -> bool:
        """Suggest marking today as cheat day when consumed > target."""
        if is_already_cheat_day:
            return False
        threshold = daily_target * WeeklyBudgetConstants.SMART_PROMPT_THRESHOLD
        return daily_consumed > threshold

    @staticmethod
    def calculate_remaining_days(week_start: date, target_date: date) -> int:
        """Calculate remaining days in the week from target date.

        Returns number of days remaining (including target date).
        """
        week_end = week_start + timedelta(days=6)
        if target_date > week_end:
            return 0
        return (week_end - target_date).days + 1
