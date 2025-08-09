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
    GenerateIngredientBasedMealPlanCommand,
    GenerateWeeklyIngredientBasedMealPlanCommand,
    ReplaceMealInPlanCommand,
)
# TDEE commands removed - not used in API
# Import from user module
from .user import (
    SaveUserOnboardingCommand,
)

__all__ = [
    # Meal commands
    "RecalculateMealNutritionCommand",
    "UploadMealImageCommand",

    # Daily meal commands
    "GenerateDailyMealSuggestionsCommand",
    "GenerateSingleMealCommand",
    # User commands
    "SaveUserOnboardingCommand",
    # Meal plan commands
    "StartMealPlanConversationCommand",
    "SendConversationMessageCommand",
    "GenerateDailyMealPlanCommand",
    "GenerateIngredientBasedMealPlanCommand",
    "GenerateWeeklyIngredientBasedMealPlanCommand",
    "ReplaceMealInPlanCommand",
]