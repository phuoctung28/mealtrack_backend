"""Generate meal suggestions handler with session tracking."""
import logging
from typing import List, Tuple

from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession

logger = logging.getLogger(__name__)


@handles(GenerateMealSuggestionsCommand)
class GenerateMealSuggestionsHandler(
    EventHandler[GenerateMealSuggestionsCommand, Tuple[SuggestionSession, List[MealSuggestion]]]
):
    """Generate initial 3 suggestions with session."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, command: GenerateMealSuggestionsCommand
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Handle generate command."""
        return await self.service.generate_suggestions(
            user_id=command.user_id,
            meal_type=command.meal_type,
            meal_size=command.meal_size,
            ingredients=command.ingredients,
            ingredient_image_url=command.ingredient_image_url,
            cooking_time_minutes=command.cooking_time_minutes,
        )
