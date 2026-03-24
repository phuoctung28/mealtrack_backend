"""
Command for streaming meal suggestion generation.
"""
from dataclasses import dataclass
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class StreamGenerateMealSuggestionsCommand(Command):
    """Command to stream meal suggestions progressively."""

    user_id: str
    meal_type: str
    meal_portion_type: str
    ingredients: List[str]
    time_available_minutes: Optional[int]
    session_id: Optional[str] = None
    language: str = "en"
    servings: int = 1
    cooking_equipment: Optional[List[str]] = None
    cuisine_region: Optional[str] = None
    calorie_target: Optional[int] = None
    protein_target: Optional[float] = None
    carbs_target: Optional[float] = None
    fat_target: Optional[float] = None

    def __post_init__(self):
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")

        valid_portion_types = ["snack", "main", "omad"]
        if self.meal_portion_type not in valid_portion_types:
            raise ValueError(f"meal_portion_type must be one of {valid_portion_types}")

        if len(self.ingredients) < 1:
            raise ValueError("ingredients list must contain at least 1 item")

        if len(self.ingredients) > 20:
            raise ValueError("ingredients list cannot exceed 20 items")

        if self.time_available_minutes is not None and self.time_available_minutes <= 0:
            raise ValueError("time_available_minutes must be greater than 0")

        if self.servings < 1 or self.servings > 4:
            raise ValueError("servings must be between 1 and 4")
