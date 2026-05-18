"""
Meal suggestion command handlers.
"""

from .discover_meals_command_handler import DiscoverMealsCommandHandler  # noqa: F401
from .generate_meal_recipes_command_handler import (  # noqa: F401
    GenerateMealRecipesCommandHandler,
)
from .save_meal_suggestion_command_handler import SaveMealSuggestionCommandHandler

__all__ = [
    "DiscoverMealsCommandHandler",
    "GenerateMealRecipesCommandHandler",
    "SaveMealSuggestionCommandHandler",
]

__all__ = [
    "SaveMealSuggestionCommandHandler",
]
