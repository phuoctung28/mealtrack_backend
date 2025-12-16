"""
Command for generating meal suggestions.
"""
from dataclasses import dataclass
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class GenerateMealSuggestionsCommand(Command):
    """
    Command to generate exactly 3 meal suggestions based on user inputs.
    
    Supports optional ingredients, time constraints, dietary preferences,
    and calorie targets. Also supports regeneration by excluding previous suggestions.
    """
    
    # User identification
    user_id: str
    
    # Required input
    meal_type: str  # breakfast, lunch, dinner, snack
    
    # Optional inputs
    ingredients: List[str]  # Available ingredients
    time_available_minutes: Optional[int]  # Time constraint
    dietary_preferences: List[str]  # Dietary preferences
    calorie_target: Optional[int]  # Calorie target for the meal
    exclude_ids: List[str]  # Meal IDs to exclude (for regeneration)
    
    def __post_init__(self):
        """Validate command data."""
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")
        
        if len(self.ingredients) > 20:
            raise ValueError("ingredients list cannot exceed 20 items")
        
        if self.time_available_minutes is not None and self.time_available_minutes <= 0:
            raise ValueError("time_available_minutes must be greater than 0")
        
        if self.calorie_target is not None and self.calorie_target <= 0:
            raise ValueError("calorie_target must be greater than 0")

