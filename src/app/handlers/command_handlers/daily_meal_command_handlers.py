"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GenerateDailyMealSuggestionsCommandHandler → generate_daily_meal_suggestions_command_handler.py
- GenerateSingleMealCommandHandler → generate_single_meal_command_handler.py

Please import from individual files or from the module.
"""
from .generate_daily_meal_suggestions_command_handler import GenerateDailyMealSuggestionsCommandHandler
from .generate_single_meal_command_handler import GenerateSingleMealCommandHandler

__all__ = [
    "GenerateDailyMealSuggestionsCommandHandler",
    "GenerateSingleMealCommandHandler"
]
