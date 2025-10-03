"""
GetConversationHistoryQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal_plan import GetConversationHistoryQuery
from src.domain.services.meal_plan_conversation_service import MealPlanConversationService

logger = logging.getLogger(__name__)


@handles(GetConversationHistoryQuery)
class GetConversationHistoryQueryHandler(EventHandler[GetConversationHistoryQuery, Dict[str, Any]]):
    """Handler for getting conversation history."""

    def __init__(self):
        self.conversation_service = MealPlanConversationService()

    def set_dependencies(self):
        """No external dependencies needed."""
        pass

    async def handle(self, query: GetConversationHistoryQuery) -> Dict[str, Any]:
        """Get conversation history."""
        conversation = self.conversation_service.get_conversation(query.conversation_id)

        if not conversation:
            raise ResourceNotFoundException(
                message="Conversation not found",
                details={"conversation_id": query.conversation_id}
            )

        return {
            "conversation": conversation
        }
