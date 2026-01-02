"""Accept suggestion command handler."""
import logging
from typing import Any, Dict

from src.app.commands.meal_suggestion import AcceptSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion import SuggestionOrchestrationService

logger = logging.getLogger(__name__)


@handles(AcceptSuggestionCommand)
class AcceptSuggestionHandler(EventHandler[AcceptSuggestionCommand, Dict[str, Any]]):
    """Accept suggestion with portion multiplier."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(self, command: AcceptSuggestionCommand) -> Dict[str, Any]:
        """Handle accept command."""
        result = await self.service.accept_suggestion(
            user_id=command.user_id,
            suggestion_id=command.suggestion_id,
            portion_multiplier=command.portion_multiplier,
            consumed_at=command.consumed_at,
        )
        return result
