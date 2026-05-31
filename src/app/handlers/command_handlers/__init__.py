"""
command_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

from .add_custom_ingredient_command_handler import AddCustomIngredientCommandHandler
from .analyze_meal_image_by_url_command_handler import AnalyzeMealImageByUrlHandler
from .complete_onboarding_command_handler import CompleteOnboardingCommandHandler

# Standalone handlers (already individual files)
from .create_manual_meal_command_handler import CreateManualMealCommandHandler
from .parse_meal_text_handler import ParseMealTextHandler
from .delete_fcm_token_command_handler import DeleteFcmTokenCommandHandler
from .delete_meal_command_handler import DeleteMealCommandHandler
from .delete_user_command_handler import DeleteUserCommandHandler

# Meal handlers (already extracted)
from .edit_meal_command_handler import EditMealCommandHandler

from .meal_suggestion import (
    DiscoverMealsCommandHandler,
    GenerateMealRecipesCommandHandler,
    SaveMealSuggestionCommandHandler,
)

# Ingredient handlers
from .recognize_ingredient_command_handler import RecognizeIngredientCommandHandler

# Notification handlers
from .register_fcm_token_command_handler import RegisterFcmTokenCommandHandler

# User handlers (newly extracted)
from .save_user_onboarding_command_handler import SaveUserOnboardingCommandHandler
from .sync_user_command_handler import SyncUserCommandHandler
from .update_notification_preferences_command_handler import (
    UpdateNotificationPreferencesCommandHandler,
)
from .update_custom_macros_command_handler import UpdateCustomMacrosCommandHandler
from .update_language_command_handler import UpdateLanguageCommandHandler
from .update_timezone_command_handler import UpdateTimezoneCommandHandler
from .update_user_last_accessed_command_handler import (
    UpdateUserLastAccessedCommandHandler,
)
from .update_user_metrics_command_handler import UpdateUserMetricsCommandHandler
from .upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)
from .saved_suggestion import (
    SaveSuggestionCommandHandler,
    DeleteSavedSuggestionCommandHandler,
)

# Hydration handlers
from .log_hydration_command_handler import LogHydrationCommandHandler
from .log_caloric_drink_command_handler import LogCaloricDrinkCommandHandler
from .delete_hydration_entry_command_handler import DeleteHydrationEntryCommandHandler

# Movement handlers
from .log_movement_command_handler import LogMovementCommandHandler
from .delete_movement_entry_command_handler import DeleteMovementEntryCommandHandler

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
    "UpdateCustomMacrosCommandHandler",
    "UpdateLanguageCommandHandler",
    "UpdateTimezoneCommandHandler",
    # Meal Suggestion handlers
    "DiscoverMealsCommandHandler",
    "GenerateMealRecipesCommandHandler",
    "SaveMealSuggestionCommandHandler",
    # Standalone handlers
    "CreateManualMealCommandHandler",
    "ParseMealTextHandler",
    "UploadMealImageImmediatelyHandler",
    "AnalyzeMealImageByUrlHandler",
    # Notification handlers
    "RegisterFcmTokenCommandHandler",
    "DeleteFcmTokenCommandHandler",
    "UpdateNotificationPreferencesCommandHandler",
    # Ingredient handlers
    "RecognizeIngredientCommandHandler",
    # Saved suggestion handlers
    "SaveSuggestionCommandHandler",
    "DeleteSavedSuggestionCommandHandler",
    # Hydration handlers
    "LogHydrationCommandHandler",
    "LogCaloricDrinkCommandHandler",
    "DeleteHydrationEntryCommandHandler",
    # Movement handlers
    "LogMovementCommandHandler",
    "DeleteMovementEntryCommandHandler",
]
