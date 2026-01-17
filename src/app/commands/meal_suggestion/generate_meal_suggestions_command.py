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
    calorie targets, and multilingual output. Also supports regeneration via session_id.
    """

    # User identification
    user_id: str

    # Required input
    meal_type: str  # breakfast, lunch, dinner, snack

    meal_portion_type: str  # snack, main, omad

    # Optional inputs
    ingredients: List[str]  # Available ingredients
    time_available_minutes: Optional[int]  # Time constraint
    session_id: Optional[str] = None  # Session ID for regeneration (auto-excludes previous meals)
    language: str = "en"  # ISO 639-1 language code (en, vi, es, fr, de, ja, zh)
    servings: int = 1  # Number of servings (1-4), scales ingredient amounts and calories
    
    def __post_init__(self):
        """Validate command data."""
        valid_meal_types = ["breakfast", "lunch", "dinner", "snack"]
        if self.meal_type not in valid_meal_types:
            raise ValueError(f"meal_type must be one of {valid_meal_types}")
        
        valid_portion_types = ["snack", "main", "omad"]
        if self.meal_portion_type not in valid_portion_types:
            raise ValueError(f"meal_portion_type must be one of {valid_portion_types}")
        
        if (len(self.ingredients) < 1):
            raise ValueError("ingredients list must contain at least 1 item")
        
        if len(self.ingredients) > 20:
            raise ValueError("ingredients list cannot exceed 20 items")
        
        if self.time_available_minutes is not None and self.time_available_minutes <= 0:
            raise ValueError("time_available_minutes must be greater than 0")

        if self.servings < 1 or self.servings > 4:
            raise ValueError("servings must be between 1 and 4")


