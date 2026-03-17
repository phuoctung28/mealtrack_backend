"""
Weekly budget service for redistribution logic and smart prompt detection.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional

from src.domain.constants import WeeklyBudgetConstants


@dataclass
class AdjustedDailyTargets:
    """Adjusted daily targets based on weekly budget consumption."""
    calories: float
    carbs: float
    fat: float
    protein: float
    bmr_floor_active: bool
    remaining_days: int


class WeeklyBudgetService:
    """Service for weekly budget calculations."""

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
        """
        Calculate adjusted daily targets based on remaining weekly budget.

        Args:
            weekly_budget: The weekly budget entity
            standard_daily_calories: Normal daily calorie target
            standard_daily_carbs: Normal daily carb target
            standard_daily_fat: Normal daily fat target
            standard_daily_protein: Normal daily protein target (stays fixed)
            bmr: Basal metabolic rate
            remaining_days: Number of days remaining in the week (including today)

        Returns:
            AdjustedDailyTargets with adjusted values
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
        """
        Calculate remaining days in the week from target date.

        Args:
            week_start: Monday of the week
            target_date: The target date

        Returns:
            Number of days remaining (including target date)
        """
        week_end = week_start + timedelta(days=6)
        if target_date > week_end:
            return 0
        return (week_end - target_date).days + 1
