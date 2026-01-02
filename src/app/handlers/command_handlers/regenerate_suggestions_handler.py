"""Regenerate suggestions handler."""
import logging
from typing import List, Tuple

from src.app.commands.meal_suggestion import RegenerateSuggestionsCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession

logger = logging.getLogger(__name__)


@handles(RegenerateSuggestionsCommand)
class RegenerateSuggestionsHandler(
    EventHandler[RegenerateSuggestionsCommand, Tuple[SuggestionSession, List[MealSuggestion]]]
):
    """Regenerate 3 NEW suggestions excluding shown."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, command: RegenerateSuggestionsCommand
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Handle regenerate command."""
        return await self.service.regenerate_suggestions(
            user_id=command.user_id,
            session_id=command.session_id,
            exclude_ids=command.exclude_ids,
        )
