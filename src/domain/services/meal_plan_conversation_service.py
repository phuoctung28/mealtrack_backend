"""
Meal plan conversation service for managing conversational meal planning.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MealPlanConversationService:
    """Service for managing meal planning conversations."""
    
    def __init__(self):
        # In-memory storage for conversations (should be replaced with persistent storage)
        self._conversations: Dict[str, Dict[str, Any]] = {}
    
    def start_conversation(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """Start a new meal planning conversation."""
        conversation = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "state": "gathering_preferences",
            "messages": [],
            "preferences": {
                "dietary_preferences": [],
                "health_conditions": [],
                "excluded_ingredients": [],
                "preferred_cuisines": [],
                "meals_per_day": None,
                "days": None,
                "calories_target": None
            },
            "current_question": "preferences"
        }
        
        self._conversations[conversation_id] = conversation
        logger.info(f"Started conversation {conversation_id} for user {user_id}")
        
        return conversation
    
    def get_initial_message(self) -> str:
        """Get the initial greeting message."""
        return (
            "Hi! I'm here to help you create a personalized meal plan. "
            "To get started, could you tell me about any dietary preferences "
            "or restrictions you have? (e.g., vegetarian, gluten-free, nut allergies)"
        )
    
    def process_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Process a user message in the conversation."""
        conversation = self._conversations.get(conversation_id)
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Add message to history
        conversation["messages"].append({
            "role": "user",
            "content": message
        })
        
        # Process based on current state
        response = self._process_based_on_state(conversation, message)
        
        # Add assistant response to history
        conversation["messages"].append({
            "role": "assistant",
            "content": response["assistant_message"]
        })
        
        return response
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation details."""
        return self._conversations.get(conversation_id)
    
    def _process_based_on_state(self, conversation: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Process message based on conversation state."""
        state = conversation["state"]
        
        if state == "gathering_preferences":
            return self._handle_preferences(conversation, message)
        elif state == "gathering_goals":
            return self._handle_goals(conversation, message)
        elif state == "gathering_details":
            return self._handle_details(conversation, message)
        elif state == "complete":
            return {
                "state": "complete",
                "assistant_message": "Your meal plan is ready! You can view it in the meal plans section.",
                "requires_input": False,
                "preferences": conversation["preferences"]
            }
        
        return {
            "state": state,
            "assistant_message": "I didn't understand that. Could you please clarify?",
            "requires_input": True
        }
    
    def _handle_preferences(self, conversation: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Handle dietary preferences gathering."""
        # Simple keyword extraction (in production, use NLP)
        message_lower = message.lower()
        
        dietary_keywords = {
            "vegetarian": "vegetarian",
            "vegan": "vegan",
            "gluten-free": "gluten-free",
            "gluten free": "gluten-free",
            "dairy-free": "dairy-free",
            "dairy free": "dairy-free",
            "keto": "keto",
            "low-carb": "low-carb",
            "low carb": "low-carb"
        }
        
        # Extract preferences
        for keyword, preference in dietary_keywords.items():
            if keyword in message_lower:
                if preference not in conversation["preferences"]["dietary_preferences"]:
                    conversation["preferences"]["dietary_preferences"].append(preference)
        
        # Check for allergies
        if any(word in message_lower for word in ["allergy", "allergic", "intolerant"]):
            if "nut" in message_lower:
                conversation["preferences"]["excluded_ingredients"].append("nuts")
            if "shellfish" in message_lower:
                conversation["preferences"]["excluded_ingredients"].append("shellfish")
            if "dairy" in message_lower:
                conversation["preferences"]["excluded_ingredients"].append("dairy")
        
        # Move to next state
        conversation["state"] = "gathering_goals"
        
        return {
            "state": "gathering_goals",
            "assistant_message": (
                "Great! Now, what's your main health or fitness goal? "
                "(e.g., lose weight, gain muscle, maintain current weight, improve energy)"
            ),
            "requires_input": True
        }
    
    def _handle_goals(self, conversation: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Handle fitness goals gathering."""
        message_lower = message.lower()
        
        # Map goals
        if any(word in message_lower for word in ["lose", "weight loss", "cut"]):
            conversation["preferences"]["fitness_goal"] = "weight_loss"
        elif any(word in message_lower for word in ["gain", "muscle", "bulk"]):
            conversation["preferences"]["fitness_goal"] = "muscle_gain"
        elif any(word in message_lower for word in ["maintain", "maintenance"]):
            conversation["preferences"]["fitness_goal"] = "maintenance"
        else:
            conversation["preferences"]["fitness_goal"] = "general_health"
        
        # Move to details
        conversation["state"] = "gathering_details"
        
        return {
            "state": "gathering_details",
            "assistant_message": (
                "Perfect! One last thing - how many days would you like me to plan for? "
                "(e.g., 1 day, 3 days, 7 days)"
            ),
            "requires_input": True
        }
    
    def _handle_details(self, conversation: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Handle meal plan details."""
        message_lower = message.lower()
        
        # Extract days
        if "1" in message or "one" in message_lower:
            conversation["preferences"]["days"] = 1
        elif "3" in message or "three" in message_lower:
            conversation["preferences"]["days"] = 3
        elif "7" in message or "seven" in message_lower or "week" in message_lower:
            conversation["preferences"]["days"] = 7
        else:
            conversation["preferences"]["days"] = 3  # Default
        
        # Mark as complete
        conversation["state"] = "complete"
        conversation["preferences"]["user_id"] = conversation["user_id"]
        
        return {
            "state": "complete",
            "assistant_message": (
                f"Excellent! I'll create a {conversation['preferences']['days']}-day meal plan "
                f"that's {', '.join(conversation['preferences']['dietary_preferences']) if conversation['preferences']['dietary_preferences'] else 'balanced'} "
                f"and aligned with your {conversation['preferences'].get('fitness_goal', 'health')} goals. "
                "Your personalized meal plan is being generated now!"
            ),
            "requires_input": False,
            "preferences": conversation["preferences"],
            "user_id": conversation["user_id"]
        }