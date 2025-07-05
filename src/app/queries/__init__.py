"""
Query definitions for CQRS pattern.
"""
# Import from activity module
from .activity import (
    GetDailyActivitiesQuery,
)
# Import from daily_meal module
from .daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery,
)
# Import from meal module
from .meal import (
    GetDailyMacrosQuery,
    GetMealByIdQuery,
    GetMealsByDateQuery,
)
# Import from meal_plan module
from .meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery,
)
# Import from tdee module
# No TDEE queries imported - all removed
# Import from user module
from .user import (
    GetUserProfileQuery,
)

__all__ = [
    # Meal queries
    "GetDailyMacrosQuery",
    "GetMealByIdQuery",
    "GetMealsByDateQuery",
    # Daily meal queries
    "GetMealSuggestionsForProfileQuery",
    "GetSingleMealForProfileQuery",
    "GetMealPlanningSummaryQuery",
    # User queries
    "GetUserProfileQuery",
    # Meal plan queries
    "GetConversationHistoryQuery",
    "GetMealPlanQuery",
    # Activity queries
    "GetDailyActivitiesQuery",
]