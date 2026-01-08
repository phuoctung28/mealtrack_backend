"""
GenerateMealSuggestionsCommandHandler - Handler for generating meal suggestions.
"""
import logging
from typing import List, Tuple

from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService

logger = logging.getLogger(__name__)


@handles(GenerateMealSuggestionsCommand)
class GenerateMealSuggestionsCommandHandler(
    EventHandler[GenerateMealSuggestionsCommand, Tuple[SuggestionSession, List[MealSuggestion]]]
):
    """Handler for generating exactly 3 meal suggestions."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, command: GenerateMealSuggestionsCommand
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """
        Generate meal suggestions based on user inputs.
        
        If session_id is provided, regenerates with automatic exclusion of previously shown meals.

        Args:
            command: GenerateMealSuggestionsCommand with user inputs

        Returns:
            Tuple of (SuggestionSession, List[MealSuggestion])
        """
        return await self.service.generate_suggestions(
            user_id=command.user_id,
            meal_type=command.meal_type,
            meal_portion_type=command.meal_portion_type,
            ingredients=command.ingredients,
            cooking_time_minutes=command.time_available_minutes,
            session_id=command.session_id,
        )