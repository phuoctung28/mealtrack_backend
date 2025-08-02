"""
Command for generating meal plans based on available ingredients and seasonings.
"""
from dataclasses import dataclass
from typing import List

from src.app.events.base import Command


@dataclass
class GenerateIngredientBasedMealPlanCommand(Command):
    """
    Command to generate a daily meal plan based on available ingredients and seasonings.
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