"""
Command for saving a meal suggestion to planned_meals table.
"""
from dataclasses import dataclass
from typing import List

from src.app.events.base import Command


@dataclass
class SaveMealSuggestionCommand(Command):
    """
    Command to save a meal suggestion to planned_meals table (daily meal plan).
    Creates MealPlan and MealPlanDay if they don't exist.
    """
    
    user_id: str
    suggestion_id: str
    name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: int
    protein: float
    carbs: float
    fat: float
    description: str | None
    estimated_cook_time_minutes: int | None
    ingredients_list: List[str]
    instructions: List[str]
    portion_multiplier: int
    meal_date: str  # YYYY-MM-DD format
    
    def __post_init__(self):
        """Validate command data."""
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")
        
        if self.calories <= 0:
            raise ValueError("calories must be greater than 0")
        
        if self.protein < 0 or self.carbs < 0 or self.fat < 0:
            raise ValueError("macros must be non-negative")
        
        if self.portion_multiplier < 1:
            raise ValueError("portion_multiplier must be at least 1")
        
        if self.estimated_cook_time_minutes is not None and self.estimated_cook_time_minutes < 0:
            raise ValueError("estimated_cook_time_minutes must be non-negative")
