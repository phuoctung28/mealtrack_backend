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

        # Check if we hit the BMR floor
        bmr_floor_active = False
        if adjusted_calories < bmr_floor:
            adjusted_calories = bmr_floor
            bmr_floor_active = True

        # Protein stays fixed regardless of weekly consumption
        adjusted_protein = standard_daily_protein

        return AdjustedDailyTargets(
            calories=round(adjusted_calories, 0),
            carbs=round(adjusted_carbs, 0),
            fat=round(adjusted_fat, 0),
            protein=round(adjusted_protein, 0),
            bmr_floor_active=bmr_floor_active,
            remaining_days=remaining_days,
        )

    @staticmethod
    def should_suggest_cheat_tag(
        daily_consumed: float,
        daily_target: float,
        meal_calories: float,
        meal_is_cheat: bool,
    ) -> Optional[str]:
        """
        Check if we should suggest tagging a meal as cheat.

        Args:
            daily_consumed: Total calories consumed today so far
            daily_target: Daily calorie target
            meal_calories: Calories of the latest meal
            meal_is_cheat: Whether the meal is already tagged as cheat

        Returns:
            Meal ID to suggest tagging, or None if no suggestion
        """
        # Don't suggest for already cheat-tagged meals
        if meal_is_cheat:
            return None

        # Check if daily consumption exceeds threshold
        threshold = daily_target * WeeklyBudgetConstants.SMART_PROMPT_THRESHOLD

        if daily_consumed > threshold:
            # Return suggestion - UI will determine which meal to suggest
            return "suggest_cheat_tag"

        return None

    @staticmethod
    def get_cheat_slots_for_goal(fitness_goal: str) -> int:
        """
        Get the number of cheat slots for a given fitness goal.

        Args:
            fitness_goal: The user's fitness goal (cut, bulk, recomp)

        Returns:
            Number of cheat meal slots per week
        """
        return WeeklyBudgetConstants.CHEAT_SLOTS_BY_GOAL.get(fitness_goal, 2)

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
