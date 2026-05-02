"""
query_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

# Activity handlers
from .get_daily_activities_query_handler import GetDailyActivitiesQueryHandler
from .get_daily_breakdown_query_handler import GetDailyBreakdownQueryHandler
from .get_daily_macros_query_handler import GetDailyMacrosQueryHandler
from .get_streak_query_handler import GetStreakQueryHandler
from .get_food_details_query_handler import GetFoodDetailsQueryHandler

# Meal handlers
from .get_meal_by_id_query_handler import GetMealByIdQueryHandler

from .get_meals_by_date_query_handler import GetMealsByDateQueryHandler

# Notification handlers
from .get_notification_preferences_query_handler import (
    GetNotificationPreferencesQueryHandler,
)
from .get_user_by_firebase_uid_query_handler import GetUserByFirebaseUidQueryHandler
from .get_user_metrics_query_handler import GetUserMetricsQueryHandler
from .get_user_onboarding_status_query_handler import (
    GetUserOnboardingStatusQueryHandler,
)

# User handlers
from .get_user_profile_query_handler import GetUserProfileQueryHandler

# TDEE handlers
from .get_user_tdee_query_handler import GetUserTdeeQueryHandler
from .preview_tdee_query_handler import PreviewTdeeQueryHandler

# Food handlers
from .lookup_barcode_query_handler import LookupBarcodeQueryHandler
from .search_foods_query_handler import SearchFoodsQueryHandler
from .get_saved_suggestions_query_handler import GetSavedSuggestionsQueryHandler
from .get_weekly_budget_query_handler import GetWeeklyBudgetQueryHandler

__all__ = [
    # TDEE
    "GetUserTdeeQueryHandler",
    "PreviewTdeeQueryHandler",
    # Food
    "SearchFoodsQueryHandler",
    "GetFoodDetailsQueryHandler",
    "LookupBarcodeQueryHandler",
    # Meal
    "GetMealByIdQueryHandler",
    "GetDailyMacrosQueryHandler",
    # User
    "GetUserProfileQueryHandler",
    "GetUserByFirebaseUidQueryHandler",
    "GetUserOnboardingStatusQueryHandler",
    "GetUserMetricsQueryHandler",
    # Activity
    "GetDailyActivitiesQueryHandler",
    # Meal Plan
    "GetMealsByDateQueryHandler",
    # Progress
    "GetStreakQueryHandler",
    "GetDailyBreakdownQueryHandler",
    # Notification
    "GetNotificationPreferencesQueryHandler",
    "GetWeeklyBudgetQueryHandler",
    # Saved suggestion
    "GetSavedSuggestionsQueryHandler",
]
