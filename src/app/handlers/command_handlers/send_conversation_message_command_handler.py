"""
SendConversationMessageCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.app.commands.meal_plan import SendConversationMessageCommand
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_plan_conversation_service import MealPlanConversationService

logger = logging.getLogger(__name__)


@handles(SendConversationMessageCommand)
class SendConversationMessageCommandHandler(EventHandler[SendConversationMessageCommand, Dict[str, Any]]):
    """Handler for sending messages in meal plan conversations."""

    def __init__(self, conversation_service: MealPlanConversationService = None):
        self.conversation_service = conversation_service or MealPlanConversationService()

    def set_dependencies(self, conversation_service: MealPlanConversationService = None):
        """Set dependencies for dependency injection."""
        if conversation_service:
            self.conversation_service = conversation_service

    async def handle(self, command: SendConversationMessageCommand) -> Dict[str, Any]:
        """Process a message in the conversation."""
        # Process message
        response = self.conversation_service.process_message(
            command.conversation_id,
            command.message
        )

        result = {
            "state": response["state"],
            "assistant_message": response["assistant_message"],
            "requires_input": response["requires_input"],
            "meal_plan_id": None,
            "events": []
        }

        # If conversation is complete, meal plan generation is disabled
        if response["state"] == "complete" and response.get("preferences"):
            # Meal plan generation removed - conversation completes without generating plan
            logger.info(f"Conversation {command.conversation_id} completed but meal plan generation is disabled")

        return result
