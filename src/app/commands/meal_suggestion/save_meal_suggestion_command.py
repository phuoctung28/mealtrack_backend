"""
Command for saving a meal suggestion as a regular meal.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class IngredientItem:
    """
    A single ingredient with quantity, unit, and optional per-item macros.

    Macros default to 0.0 when not provided. Populate them whenever available
    so that ingredient-level edits can recalculate meal totals later.
    """

    name: str
    amount: float
    unit: str
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0


@dataclass
class SaveMealSuggestionCommand(Command):
    """Command to save a meal suggestion as a regular Meal entity."""

    user_id: str
    suggestion_id: str
    name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: int
    protein: float
    carbs: float
    fat: float
    description: Optional[str]
    estimated_cook_time_minutes: Optional[int]
    ingredients: List[IngredientItem]
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
