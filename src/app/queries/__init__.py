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
    SearchMealsQuery,
)
# Import from meal_plan module
from .meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery,
)
# Import from tdee module
from .tdee import (
    GetMacroTargetsQuery,
    CompareTdeeMethodsQuery,
)
# Import from user module
from .user import (
    GetOnboardingSectionsQuery,
    GetUserProfileQuery,
)

__all__ = [
    # Meal queries
    "GetDailyMacrosQuery",
    "GetMealByIdQuery",
    "GetMealsByDateQuery",
    "SearchMealsQuery",
    # TDEE queries
    "GetMacroTargetsQuery",
    "CompareTdeeMethodsQuery",
    # Daily meal queries
    "GetMealSuggestionsForProfileQuery",
    "GetSingleMealForProfileQuery",
    "GetMealPlanningSummaryQuery",
    # User queries
    "GetOnboardingSectionsQuery",
    "GetUserProfileQuery",
    # Meal plan queries
    "GetConversationHistoryQuery",
    "GetMealPlanQuery",
    # Activity queries
    "GetDailyActivitiesQuery",
]