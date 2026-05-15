"""
Command for generating lightweight meal discovery options.
"""

from dataclasses import dataclass
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class DiscoverMealsCommand(Command):
    """Generate a discovery batch of meal names and macro estimates."""

    user_id: str
    meal_type: str
    meal_portion_type: str
    ingredients: List[str]
    time_available_minutes: Optional[int]
    session_id: Optional[str] = None
    language: str = "en"
    cuisine_region: Optional[str] = None
    calorie_target: Optional[int] = None
    protein_target: Optional[float] = None
    carbs_target: Optional[float] = None
    fat_target: Optional[float] = None
    count: int = 6

    def __post_init__(self):
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")

        valid_portion_types = ["snack", "main", "omad"]
        if self.meal_portion_type not in valid_portion_types:
            raise ValueError(f"meal_portion_type must be one of {valid_portion_types}")

        if len(self.ingredients) > 20:
            raise ValueError("ingredients list cannot exceed 20 items")

        if self.time_available_minutes is not None and self.time_available_minutes <= 0:
            raise ValueError("time_available_minutes must be greater than 0")

        if self.count < 1 or self.count > 8:
            raise ValueError("count must be between 1 and 8")
