"""Reject suggestion command handler."""
import logging

from src.app.commands.meal_suggestion import RejectSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion import SuggestionOrchestrationService

logger = logging.getLogger(__name__)


@handles(RejectSuggestionCommand)
class RejectSuggestionHandler(EventHandler[RejectSuggestionCommand, None]):
    """Reject suggestion."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(self, command: RejectSuggestionCommand) -> None:
        """Handle reject command."""
        await self.service.reject_suggestion(
            user_id=command.user_id,
            suggestion_id=command.suggestion_id,
            feedback=command.feedback,
        )
