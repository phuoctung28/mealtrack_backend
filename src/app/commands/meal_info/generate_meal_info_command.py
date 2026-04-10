"""Command for generating lightweight meal info (name + description + image)."""
from dataclasses import dataclass
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class GenerateMealInfoCommand(Command):
    """
    Generate a MealInfo: meal name, nutrition description, and image URL.

    Either meal_name or ingredients must be provided.
    Macros are optional — when given, the nutrition description is rule-based;
    otherwise it is AI-generated from the meal name.
    """

    user_id: str

    # One of these must be provided
    meal_name: Optional[str] = None
    ingredients: Optional[List[str]] = None

    meal_type: str = "lunch"
    language: str = "en"

    # Optional macros for rule-based description
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

    def __post_init__(self):
        if not self.meal_name and not self.ingredients:
            raise ValueError("Either meal_name or ingredients must be provided.")

        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")

        if self.ingredients and len(self.ingredients) > 20:
            raise ValueError("ingredients list cannot exceed 20 items.")

        for field_name, value in [("calories", self.calories), ("protein", self.protein),
                                   ("carbs", self.carbs), ("fat", self.fat)]:
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative.")
