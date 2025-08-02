"""
Command for generating weekly meal plans based on available ingredients and seasonings.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from src.app.events.base import Command


@dataclass
class GenerateWeeklyIngredientBasedMealPlanCommand(Command):
    """
    Command to generate a weekly meal plan (Monday to Sunday) based on available ingredients and seasonings.
    All other preferences are retrieved from the user's profile.
    """
    # User identification
    user_id: str

    # Only ingredient data - everything else comes from user profile
    available_ingredients: List[str]  # List of ingredient names
    available_seasonings: List[str]  # List of seasoning names
    
    def __post_init__(self):
        """Validate command data."""
        if not self.available_ingredients:
            raise ValueError("At least one ingredient must be provided") 