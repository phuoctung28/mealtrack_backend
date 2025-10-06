"""
command_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

from .add_custom_ingredient_handler import AddCustomIngredientCommandHandler
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler
# Standalone handlers (already individual files)
from .create_manual_meal_command_handler import CreateManualMealCommandHandler
from .delete_meal_handler import DeleteMealCommandHandler
# Meal handlers (already extracted)
from .edit_meal_handler import EditMealCommandHandler
# Daily Meal handlers (newly extracted)
from .generate_daily_meal_suggestions_command_handler import GenerateDailyMealSuggestionsCommandHandler
from .generate_single_meal_command_handler import GenerateSingleMealCommandHandler
# User handlers (newly extracted)
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_user_last_accessed_command_handler import UpdateUserLastAccessedCommandHandler
from .upload_meal_image_immediately_handler import UploadMealImageImmediatelyHandler
from .weekly_ingredient_based_meal_plan_command_handler import GenerateWeeklyIngredientBasedMealPlanCommandHandler
from .update_user_metrics_command_handler import UpdateUserMetricsCommandHandler

__all__ = [
    # Meal handlers
    "EditMealCommandHandler",
    "AddCustomIngredientCommandHandler",
    "DeleteMealCommandHandler",
    # User handlers
    "SaveUserOnboardingCommandHandler",
    "SyncUserCommandHandler",
    "UpdateUserLastAccessedCommandHandler",
    "CompleteOnboardingCommandHandler",
    "UpdateUserMetricsCommandHandler",
    # Daily Meal handlers
    "GenerateDailyMealSuggestionsCommandHandler",
    "GenerateSingleMealCommandHandler",
    # Standalone handlers
    "CreateManualMealCommandHandler",
    "GenerateWeeklyIngredientBasedMealPlanCommandHandler",
    "UploadMealImageImmediatelyHandler",
]
