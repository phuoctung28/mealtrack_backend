"""Discard session command handler."""
import logging

from src.app.commands.meal_suggestion import DiscardSessionCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService

logger = logging.getLogger(__name__)


@handles(DiscardSessionCommand)
class DiscardSessionHandler(EventHandler[DiscardSessionCommand, None]):
    """Discard session."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(self, command: DiscardSessionCommand) -> None:
        """Handle discard command."""
        await self.service.discard_session(
            user_id=command.user_id,
            session_id=command.session_id,
        )
