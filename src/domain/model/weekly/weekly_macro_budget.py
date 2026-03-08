"""
Weekly macro budget domain entity.

This entity tracks weekly macro consumption against budget targets.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class WeeklyMacroBudget:
    """Domain entity for weekly macro budget tracking."""

    weekly_budget_id: str
    user_id: str
    week_start_date: date

    # Target values (daily × 7)
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float

    # Consumed values
    consumed_calories: float = 0.0
    consumed_protein: float = 0.0
    consumed_carbs: float = 0.0
    consumed_fat: float = 0.0

    # Metadata
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    @property
    def remaining_calories(self) -> float:
        """Calculate remaining calories for the week."""
        return max(0, self.target_calories - self.consumed_calories)

    @property
    def remaining_protein(self) -> float:
        """Calculate remaining protein for the week."""
        return max(0, self.target_protein - self.consumed_protein)

    @property
    def remaining_carbs(self) -> float:
        """Calculate remaining carbs for the week."""
        return max(0, self.target_carbs - self.consumed_carbs)

    @property
    def remaining_fat(self) -> float:
        """Calculate remaining fat for the week."""
        return max(0, self.target_fat - self.consumed_fat)

    @property
    def consumption_percentage(self) -> float:
        """Calculate percentage of weekly budget consumed."""
        if self.target_calories == 0:
            return 0
        return (self.consumed_calories / self.target_calories) * 100

    @property
    def is_over_budget(self) -> bool:
        """Check if user is over budget."""
        return self.consumed_calories > self.target_calories

    def add_consumed(self, calories: float, protein: float, carbs: float, fat: float):
        """Add consumed macros to the weekly total."""
        self.consumed_calories += calories
        self.consumed_protein += protein
        self.consumed_carbs += carbs
        self.consumed_fat += fat

    def calculate_adjusted_daily(
        self,
        standard_daily_calories: float,
        standard_daily_carbs: float,
        standard_daily_fat: float,
        bmr: float,
        remaining_days: int,
    ) -> dict:
        """
        Calculate adjusted daily targets based on remaining weekly budget.

        Args:
            standard_daily_calories: Normal daily calorie target
            standard_daily_carbs: Normal daily carb target
            standard_daily_fat: Normal daily fat target
            bmr: Basal metabolic rate
            remaining_days: Number of days remaining in the week (including today)

        Returns:
            dict with adjusted values and bmr_floor_active flag
        """
        if remaining_days <= 0:
            remaining_days = 1

        # Calculate BMR floor
        bmr_floor = max(bmr, standard_daily_calories * 0.80)

        # Redistribute remaining weekly budget
        adjusted_calories = self.remaining_calories / remaining_days
        adjusted_carbs = self.remaining_carbs / remaining_days
        adjusted_fat = self.remaining_fat / remaining_days

        # Check if we hit the BMR floor
        bmr_floor_active = False
        if adjusted_calories < bmr_floor:
            adjusted_calories = bmr_floor
            bmr_floor_active = True

        # Carbs and fat follow proportionally but also capped at reasonable levels
        # (we don't enforce floor on carbs/fat, only calories)

        return {
            "adjusted_calories": round(adjusted_calories, 0),
            "adjusted_carbs": round(adjusted_carbs, 0),
            "adjusted_fat": round(adjusted_fat, 0),
            "bmr_floor_active": bmr_floor_active,
            "remaining_days": remaining_days,
        }
