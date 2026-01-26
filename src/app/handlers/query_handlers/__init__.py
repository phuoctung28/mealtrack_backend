"""
query_handlers - Individual handler files.
Each handler is in its own file for better maintainability.
"""

# Activity handlers
from .get_daily_activities_query_handler import GetDailyActivitiesQueryHandler
from .get_daily_macros_query_handler import GetDailyMacrosQueryHandler
from .get_food_details_query_handler import GetFoodDetailsQueryHandler
# Meal handlers
from .get_meal_by_id_query_handler import GetMealByIdQueryHandler
# Meal Plan handlers
from .get_meal_plan_query_handler import GetMealPlanQueryHandler
from .get_meal_planning_summary_query_handler import GetMealPlanningSummaryQueryHandler
# Daily Meal handlers
from .get_meal_suggestions_for_profile_query_handler import GetMealSuggestionsForProfileQueryHandler
from .get_meals_by_date_query_handler import GetMealsByDateQueryHandler
from .get_meals_from_plan_by_date_query_handler import GetMealsFromPlanByDateQueryHandler
# Notification handlers
from .get_notification_preferences_query_handler import GetNotificationPreferencesQueryHandler
from .get_single_meal_for_profile_query_handler import GetSingleMealForProfileQueryHandler
from .get_user_by_firebase_uid_query_handler import GetUserByFirebaseUidQueryHandler
from .get_user_metrics_query_handler import GetUserMetricsQueryHandler
from .get_user_onboarding_status_query_handler import GetUserOnboardingStatusQueryHandler
# User handlers
from .get_user_profile_query_handler import GetUserProfileQueryHandler
# TDEE handlers
from .get_user_tdee_query_handler import GetUserTdeeQueryHandler
from .preview_tdee_query_handler import PreviewTdeeQueryHandler
# Food handlers
from .search_foods_query_handler import SearchFoodsQueryHandler

__all__ = [
    # TDEE
    "GetUserTdeeQueryHandler",
    "PreviewTdeeQueryHandler",
    # Food
    "SearchFoodsQueryHandler",
    "GetFoodDetailsQueryHandler",
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
    "GetMealPlanQueryHandler",
    "GetMealsFromPlanByDateQueryHandler",
    "GetMealsByDateQueryHandler",
    # Daily Meal
    "GetMealSuggestionsForProfileQueryHandler",
    "GetSingleMealForProfileQueryHandler",
    "GetMealPlanningSummaryQueryHandler",
    # Notification
    "GetNotificationPreferencesQueryHandler",
]
