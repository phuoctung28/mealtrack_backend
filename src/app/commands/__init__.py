"""
Command definitions for CQRS pattern.
"""

# Import from meal_suggestion module
from .meal_suggestion import GenerateMealSuggestionsCommand

# TDEE commands removed - not used in API
# Import from user module
from .user import (
    SaveUserOnboardingCommand,
)

__all__ = [
    # User commands
    "SaveUserOnboardingCommand",
    # Meal suggestion commands
    "GenerateMealSuggestionsCommand",
]
