"""
GetSingleMealForProfileQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.daily_meal import GetSingleMealForProfileQuery, GetMealSuggestionsForProfileQuery
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService

logger = logging.getLogger(__name__)


@handles(GetSingleMealForProfileQuery)
class GetSingleMealForProfileQueryHandler(EventHandler[GetSingleMealForProfileQuery, Dict[str, Any]]):
    """Handler for getting a single meal suggestion for a profile."""

    def __init__(self):
        self.suggestion_service = DailyMealSuggestionService()

    async def handle(self, query: GetSingleMealForProfileQuery) -> Dict[str, Any]:
        """Get a single meal suggestion for a profile."""
        # Use the profile suggestions handler to get all meals
        from src.app.handlers.query_handlers.get_meal_suggestions_for_profile_query_handler import GetMealSuggestionsForProfileQueryHandler

        profile_handler = GetMealSuggestionsForProfileQueryHandler()
        all_suggestions = await profile_handler.handle(
            GetMealSuggestionsForProfileQuery(user_profile_id=query.user_profile_id)
        )

        # Find the requested meal type
        for meal in all_suggestions["meals"]:
            if meal["meal_type"].lower() == query.meal_type.lower():
                return {
                    "success": True,
                    "meal": meal
                }

        raise ValueError(f"No {query.meal_type} suggestion found for profile")
