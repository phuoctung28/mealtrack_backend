"""
Command for generating recipes for selected discovery meals.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.app.events.base import Command


@dataclass
class GenerateMealRecipesCommand(Command):
    """Generate full recipes for selected discovery meals or legacy names."""

    user_id: str
    meal_type: str
    language: str
    meal_names: list[str] = field(default_factory=list)
    session_id: Optional[str] = None
    selected_meal_ids: list[str] = field(default_factory=list)
    selected_meals: list[dict] = field(default_factory=list)
    ingredients: list[str] = field(default_factory=list)
    cooking_time_minutes: Optional[int] = None
    cuisine_region: Optional[str] = None
    calorie_target: Optional[int] = None
    protein_target: Optional[float] = None
    carbs_target: Optional[float] = None
    fat_target: Optional[float] = None

    def __post_init__(self):
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")

        if (
            not self.selected_meal_ids
            and not self.selected_meals
            and not self.meal_names
        ):
            raise ValueError("Provide selected_meal_ids, selected_meals, or meal_names")

        if len(self.meal_names) > 3:
            raise ValueError("meal_names cannot exceed 3 items")
        if len(self.selected_meal_ids) > 3:
            raise ValueError("selected_meal_ids cannot exceed 3 items")
        if len(self.selected_meals) > 3:
            raise ValueError("selected_meals cannot exceed 3 items")
