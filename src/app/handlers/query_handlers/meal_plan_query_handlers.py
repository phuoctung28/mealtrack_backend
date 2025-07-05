"""
Query handlers for meal plan domain - read operations.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery
)
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


@handles(GetMealPlanQuery)
class GetMealPlanQueryHandler(EventHandler[GetMealPlanQuery, Dict[str, Any]]):
    """Handler for getting meal plans."""
    
    def __init__(self):
        # In-memory storage for demo
        self._meal_plans: Dict[str, Dict[str, Any]] = {}
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
    async def handle(self, query: GetMealPlanQuery) -> Dict[str, Any]:
        """Get a meal plan by ID."""
        # For demo purposes, return not found
        # In production, this would fetch from database
        raise ResourceNotFoundException(
            message="Meal plan not found",
            details={"plan_id": query.plan_id}
        )
        
        return {
            "meal_plan": meal_plan
        }