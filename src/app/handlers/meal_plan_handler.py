import logging
from datetime import date
from typing import Dict, Optional

from src.domain.model.meal_plan import UserPreferences
from src.domain.services.conversation_service import ConversationService
from src.domain.services.meal_plan_service import MealPlanService

logger = logging.getLogger(__name__)


class MealPlanHandler:
    """Handler for meal plan operations"""
    
    def __init__(self, meal_plan_service: MealPlanService):
        self.meal_plan_service = meal_plan_service
    
    def generate_meal_plan(self, user_id: str, preferences: UserPreferences) -> Dict:
        """Generate a new meal plan"""
        try:
            logger.info(f"Generating meal plan for user {user_id}")
            
            # Generate meal plan
            meal_plan = self.meal_plan_service.generate_meal_plan(
                user_id=user_id,
                preferences=preferences
            )
            
            # Return meal plan as dict
            return {
                "success": True,
                "meal_plan": meal_plan.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return {
                "success": False,
                "error": "Failed to generate meal plan",
                "message": str(e)
            }
    
    def get_meal_plan(self, plan_id: str) -> Dict:
        """Get an existing meal plan"""
        # In a real implementation, this would fetch from database
        # For now, return a placeholder
        return {
            "success": False,
            "error": "Not implemented",
            "message": "Meal plan retrieval not yet implemented"
        }
    
    def regenerate_meal(self, plan_id: str, date: date, meal_id: str, 
                       additional_preferences: Optional[Dict] = None) -> Dict:
        """Regenerate a specific meal in a plan"""
        try:
            # In a real implementation, fetch meal plan from database
            # For now, return error
            return {
                "success": False,
                "error": "Not implemented",
                "message": "Meal regeneration not yet implemented"
            }
            
        except Exception as e:
            logger.error(f"Error regenerating meal: {str(e)}")
            return {
                "success": False,
                "error": "Failed to regenerate meal",
                "message": str(e)
            }


class ConversationHandler:
    """Handler for meal planning conversations"""
    
    def __init__(self, conversation_service: ConversationService):
        self.conversation_service = conversation_service
        # In-memory storage for demo - in production use database
        self.conversations = {}
    
    def start_conversation(self, user_id: str) -> Dict:
        """Start a new meal planning conversation"""
        try:
            conversation = self.conversation_service.start_conversation(user_id)
            
            # Store conversation
            self.conversations[conversation.conversation_id] = conversation
            
            return {
                "success": True,
                "conversation_id": conversation.conversation_id,
                "state": conversation.state.value,
                "assistant_message": conversation.get_last_assistant_message().content
            }
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {
                "success": False,
                "error": "Failed to start conversation",
                "message": str(e)
            }
    
    def process_message(self, conversation_id: str, user_message: str) -> Dict:
        """Process a user message in a conversation"""
        try:
            # Get conversation
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found",
                    "message": "Please start a new conversation"
                }
            
            # Process message
            assistant_message, requires_input, meal_plan_id = self.conversation_service.process_message(
                conversation=conversation,
                user_message=user_message
            )
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "state": conversation.state.value,
                "assistant_message": assistant_message,
                "requires_input": requires_input,
                "meal_plan_id": meal_plan_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "success": False,
                "error": "Failed to process message",
                "message": str(e)
            }
    
    def get_conversation_history(self, conversation_id: str) -> Dict:
        """Get conversation history"""
        try:
            conversation = self.conversations.get(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found",
                    "message": "Conversation ID not found"
                }
            
            return {
                "success": True,
                "conversation": conversation.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return {
                "success": False,
                "error": "Failed to get conversation history",
                "message": str(e)
            }