"""
StartMealPlanConversationCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any
from uuid import uuid4

from src.app.commands.meal_plan import StartMealPlanConversationCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal_plan import ConversationStartedEvent
from src.domain.services.meal_plan_conversation_service import MealPlanConversationService

logger = logging.getLogger(__name__)


@handles(StartMealPlanConversationCommand)
class StartMealPlanConversationCommandHandler(EventHandler[StartMealPlanConversationCommand, Dict[str, Any]]):
    """Handler for starting meal plan conversations."""

    def __init__(self, conversation_service: MealPlanConversationService = None):
        self.conversation_service = conversation_service or MealPlanConversationService()

    def set_dependencies(self, conversation_service: MealPlanConversationService = None):
        """Set dependencies for dependency injection."""
        if conversation_service:
            self.conversation_service = conversation_service

    async def handle(self, command: StartMealPlanConversationCommand) -> Dict[str, Any]:
        """Start a new meal planning conversation."""
        # Create conversation
        conversation_id = str(uuid4())
        conversation = self.conversation_service.start_conversation(conversation_id, command.user_id)

        # Get initial message
        assistant_message = self.conversation_service.get_initial_message()

        result = {
            "conversation_id": conversation_id,
            "state": conversation["state"],
            "assistant_message": assistant_message,
            "events": [
                ConversationStartedEvent(
                    aggregate_id=conversation_id,
                    conversation_id=conversation_id,
                    user_id=command.user_id,
                    initial_state=conversation["state"]
                )
            ]
        }

        logger.info(f"Started conversation {conversation_id} for user {command.user_id}")
        return result
