"""
command_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

# Meal handlers (already extracted)
from .upload_meal_image_handler import UploadMealImageCommandHandler
from .recalculate_meal_nutrition_handler import RecalculateMealNutritionCommandHandler
from .edit_meal_handler import EditMealCommandHandler
from .add_custom_ingredient_handler import AddCustomIngredientCommandHandler
from .delete_meal_handler import DeleteMealCommandHandler

# User handlers (newly extracted)
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_user_last_accessed_command_handler import UpdateUserLastAccessedCommandHandler
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler

# Meal Plan handlers (newly extracted)
from .start_meal_plan_conversation_command_handler import StartMealPlanConversationCommandHandler
from .send_conversation_message_command_handler import SendConversationMessageCommandHandler
from .replace_meal_in_plan_command_handler import ReplaceMealInPlanCommandHandler
from .generate_daily_meal_plan_command_handler import GenerateDailyMealPlanCommandHandler

# Daily Meal handlers (newly extracted)
from .generate_daily_meal_suggestions_command_handler import GenerateDailyMealSuggestionsCommandHandler
from .generate_single_meal_command_handler import GenerateSingleMealCommandHandler

# Standalone handlers (already individual files)
from .create_manual_meal_command_handler import CreateManualMealCommandHandler
from .ingredient_based_meal_plan_command_handler import GenerateIngredientBasedMealPlanCommandHandler
from .weekly_ingredient_based_meal_plan_command_handler import GenerateWeeklyIngredientBasedMealPlanCommandHandler
from .upload_meal_image_immediately_handler import UploadMealImageImmediatelyHandler

__all__ = [
    # Meal handlers
    "UploadMealImageCommandHandler",
    "RecalculateMealNutritionCommandHandler",
    "EditMealCommandHandler",
    "AddCustomIngredientCommandHandler",
    "DeleteMealCommandHandler",
    # User handlers
    "SaveUserOnboardingCommandHandler",
    "SyncUserCommandHandler",
    "UpdateUserLastAccessedCommandHandler",
    "CompleteOnboardingCommandHandler",
    # Meal Plan handlers
    "StartMealPlanConversationCommandHandler",
    "SendConversationMessageCommandHandler",
    "ReplaceMealInPlanCommandHandler",
    "GenerateDailyMealPlanCommandHandler",
    # Daily Meal handlers
    "GenerateDailyMealSuggestionsCommandHandler",
    "GenerateSingleMealCommandHandler",
    # Standalone handlers
    "CreateManualMealCommandHandler",
    "GenerateIngredientBasedMealPlanCommandHandler",
    "GenerateWeeklyIngredientBasedMealPlanCommandHandler",
    "UploadMealImageImmediatelyHandler",
]
