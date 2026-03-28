"""
Weekly macro budget domain entity.

This entity tracks weekly macro consumption against budget targets.
"""
from dataclasses import dataclass
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
        """Calculate remaining calories for the week. Can be negative when over budget."""
        return self.target_calories - self.consumed_calories

    @property
    def remaining_protein(self) -> float:
        """Calculate remaining protein for the week. Can be negative when over-consumed."""
        return self.target_protein - self.consumed_protein

    @property
    def remaining_carbs(self) -> float:
        """Calculate remaining carbs for the week. Can be negative when over-consumed."""
        return self.target_carbs - self.consumed_carbs

    @property
    def remaining_fat(self) -> float:
        """Calculate remaining fat for the week. Can be negative when over-consumed."""
        return self.target_fat - self.consumed_fat

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

