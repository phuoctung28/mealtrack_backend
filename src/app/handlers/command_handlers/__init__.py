"""
command_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

from .add_custom_ingredient_command_handler import AddCustomIngredientCommandHandler
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler
# Standalone handlers (already individual files)
from .create_manual_meal_command_handler import CreateManualMealCommandHandler
from .delete_fcm_token_command_handler import DeleteFcmTokenCommandHandler
from .delete_meal_command_handler import DeleteMealCommandHandler
from .delete_user_command_handler import DeleteUserCommandHandler
# Meal handlers (already extracted)
from .edit_meal_command_handler import EditMealCommandHandler
# Daily Meal handlers (newly extracted)
from .generate_daily_meal_suggestions_command_handler import GenerateDailyMealSuggestionsCommandHandler
# Meal Suggestion handlers (supports both initial generation and regeneration via session_id)
from .generate_meal_suggestions_command_handler import GenerateMealSuggestionsCommandHandler
from .meal_suggestion.save_meal_suggestion_command_handler import SaveMealSuggestionCommandHandler
from .generate_single_meal_command_handler import GenerateSingleMealCommandHandler
# Ingredient handlers
from .recognize_ingredient_command_handler import RecognizeIngredientCommandHandler
# Notification handlers
from .register_fcm_token_command_handler import RegisterFcmTokenCommandHandler
# User handlers (newly extracted)
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_notification_preferences_command_handler import UpdateNotificationPreferencesCommandHandler
from .update_user_last_accessed_command_handler import UpdateUserLastAccessedCommandHandler
from .update_user_metrics_command_handler import UpdateUserMetricsCommandHandler
from .upload_meal_image_immediately_command_handler import UploadMealImageImmediatelyHandler
from .weekly_ingredient_based_meal_plan_command_handler import GenerateWeeklyIngredientBasedMealPlanCommandHandler

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
    "DeleteUserCommandHandler",
    "UpdateUserMetricsCommandHandler",
    # Daily Meal handlers
    "GenerateDailyMealSuggestionsCommandHandler",
    "GenerateSingleMealCommandHandler",
    # Meal Suggestion handlers (supports both initial generation and regeneration via session_id)
    "GenerateMealSuggestionsCommandHandler",
    "SaveMealSuggestionCommandHandler",
    # Standalone handlers
    "CreateManualMealCommandHandler",
    "GenerateWeeklyIngredientBasedMealPlanCommandHandler",
    "UploadMealImageImmediatelyHandler",
    # Notification handlers
    "RegisterFcmTokenCommandHandler",
    "DeleteFcmTokenCommandHandler",
    "UpdateNotificationPreferencesCommandHandler",
    # Ingredient handlers
    "RecognizeIngredientCommandHandler",
]
