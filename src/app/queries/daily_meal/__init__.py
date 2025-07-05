"""Daily meal queries."""
from .get_meal_planning_summary_query import GetMealPlanningSummaryQuery
from .get_meal_suggestions_for_profile_query import GetMealSuggestionsForProfileQuery
from .get_single_meal_for_profile_query import GetSingleMealForProfileQuery

__all__ = [
    "GetMealSuggestionsForProfileQuery",
    "GetSingleMealForProfileQuery",
    "GetMealPlanningSummaryQuery",
]