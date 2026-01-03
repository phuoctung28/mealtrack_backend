"""
command_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

from .add_custom_ingredient_command_handler import AddCustomIngredientCommandHandler
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler
from .delete_user_command_handler import DeleteUserCommandHandler
# Standalone handlers (already individual files)
from .create_manual_meal_command_handler import CreateManualMealCommandHandler
from .delete_meal_command_handler import DeleteMealCommandHandler
# Meal handlers (already extracted)
from .edit_meal_command_handler import EditMealCommandHandler
# Daily Meal handlers (newly extracted)
from .generate_daily_meal_suggestions_command_handler import GenerateDailyMealSuggestionsCommandHandler
from .generate_single_meal_command_handler import GenerateSingleMealCommandHandler
# Meal Suggestion handlers (legacy)
from .generate_meal_suggestions_command_handler import GenerateMealSuggestionsCommandHandler
from .save_meal_suggestion_command_handler import SaveMealSuggestionCommandHandler
# Session-based suggestion handlers (new orchestration-based)
from .accept_suggestion_handler import AcceptSuggestionHandler
from .discard_session_handler import DiscardSessionHandler
from .get_session_suggestions_handler import GetSessionSuggestionsHandler
from .regenerate_suggestions_handler import RegenerateSuggestionsHandler
from .reject_suggestion_handler import RejectSuggestionHandler
# User handlers (newly extracted)
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_user_last_accessed_command_handler import UpdateUserLastAccessedCommandHandler
from .update_user_metrics_command_handler import UpdateUserMetricsCommandHandler
from .upload_meal_image_immediately_command_handler import UploadMealImageImmediatelyHandler
from .weekly_ingredient_based_meal_plan_command_handler import GenerateWeeklyIngredientBasedMealPlanCommandHandler
# Notification handlers
from .register_fcm_token_command_handler import RegisterFcmTokenCommandHandler
from .delete_fcm_token_command_handler import DeleteFcmTokenCommandHandler
from .update_notification_preferences_command_handler import UpdateNotificationPreferencesCommandHandler
# Ingredient handlers
from .recognize_ingredient_command_handler import RecognizeIngredientCommandHandler

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
    # Meal Suggestion handlers (legacy)
    "GenerateMealSuggestionsCommandHandler",
    "SaveMealSuggestionCommandHandler",
    # Session-based suggestion handlers (new orchestration-based)
    "RegenerateSuggestionsHandler",
    "GetSessionSuggestionsHandler",
    "AcceptSuggestionHandler",
    "RejectSuggestionHandler",
    "DiscardSessionHandler",
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
