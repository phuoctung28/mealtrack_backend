"""
Command definitions for CQRS pattern.
"""
# Import from daily_meal module
from .daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)

# Import from meal_suggestion module
from .meal_suggestion import GenerateMealSuggestionsCommand
# TDEE commands removed - not used in API
# Import from user module
from .user import (
    SaveUserOnboardingCommand,
)

__all__ = [
    # Daily meal commands
    "GenerateDailyMealSuggestionsCommand",
    "GenerateSingleMealCommand",
    # User commands
    "SaveUserOnboardingCommand",
    # Meal suggestion commands
    "GenerateMealSuggestionsCommand",
]