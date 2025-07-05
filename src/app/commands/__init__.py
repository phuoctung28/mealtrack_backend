"""
Command definitions for CQRS pattern.
"""
# Import from daily_meal module
from .daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)
# Import from meal module
from .meal import (
    RecalculateMealNutritionCommand,
    UploadMealImageCommand,
)
# Import from meal_plan module
from .meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    GenerateMealPlanCommand,
    ReplaceMealInPlanCommand,
)
# Import from tdee module
from .tdee import (
    CalculateTdeeCommand,
)
# Import from user module
from .user import (
    SaveUserOnboardingCommand,
)

__all__ = [
    # Meal commands
    "RecalculateMealNutritionCommand",
    "UploadMealImageCommand",
    # TDEE commands
    "CalculateTdeeCommand",
    # Daily meal commands
    "GenerateDailyMealSuggestionsCommand",
    "GenerateSingleMealCommand",
    # User commands
    "SaveUserOnboardingCommand",
    # Meal plan commands
    "StartMealPlanConversationCommand",
    "SendConversationMessageCommand",
    "GenerateMealPlanCommand",
    "ReplaceMealInPlanCommand",
]