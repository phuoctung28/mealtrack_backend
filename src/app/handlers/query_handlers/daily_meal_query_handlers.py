"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetMealSuggestionsForProfileQueryHandler → get_meal_suggestions_for_profile_query_handler.py
- GetSingleMealForProfileQueryHandler → get_single_meal_for_profile_query_handler.py
- GetMealPlanningSummaryQueryHandler → get_meal_planning_summary_query_handler.py

Please import from individual files or from the module.
"""
from .get_meal_suggestions_for_profile_query_handler import GetMealSuggestionsForProfileQueryHandler
from .get_single_meal_for_profile_query_handler import GetSingleMealForProfileQueryHandler
from .get_meal_planning_summary_query_handler import GetMealPlanningSummaryQueryHandler

__all__ = [
    "GetMealSuggestionsForProfileQueryHandler",
    "GetSingleMealForProfileQueryHandler",
    "GetMealPlanningSummaryQueryHandler"
]
