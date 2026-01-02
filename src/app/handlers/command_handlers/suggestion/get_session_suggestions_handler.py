"""Get session suggestions query handler."""
import logging
from typing import List, Tuple

from src.app.queries.meal_suggestion import GetSessionSuggestionsQuery
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion import SuggestionOrchestrationService
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession

logger = logging.getLogger(__name__)


@handles(GetSessionSuggestionsQuery)
class GetSessionSuggestionsHandler(
    EventHandler[GetSessionSuggestionsQuery, Tuple[SuggestionSession, List[MealSuggestion]]]
):
    """Get current session suggestions."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, query: GetSessionSuggestionsQuery
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Handle query."""
        return await self.service.get_session_suggestions(
            user_id=query.user_id,
            session_id=query.session_id,
        )
