"""
Command for saving a meal suggestion to meal history.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional, List

from src.app.events.base import Command


@dataclass
class SaveMealSuggestionCommand(Command):
    """
    Command to save a selected meal suggestion to the user's meal history.
    
    Saves the suggestion as a planned meal in the database.
    """
    
    # User identification
    user_id: str
    
    # Suggestion data
    suggestion_id: str
    name: str
    description: str
    meal_type: str  # breakfast, lunch, dinner, snack
    estimated_cook_time_minutes: int
    calories: int
    protein: float
    carbs: float
    fat: float
    ingredients_list: List[str]
    instructions: List[str]
    
    # Optional date (defaults to today)
    meal_date: Optional[date] = None
    
    def __post_init__(self):
        """Validate command data."""
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")
        
        if self.estimated_cook_time_minutes <= 0:
            raise ValueError("estimated_cook_time_minutes must be greater than 0")
        
        if self.calories <= 0:
            raise ValueError("calories must be greater than 0")
        
        # Set default date if not provided
        if self.meal_date is None:
            object.__setattr__(self, 'meal_date', date.today())


