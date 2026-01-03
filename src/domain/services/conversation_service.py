"""Service for managing meal planning conversations."""
import logging
from typing import Optional, Tuple

from src.domain.model.conversation import Conversation, ConversationState, MessageRole
from src.domain.services.conversation.conversation_handler import ConversationHandler
from src.domain.services.meal_plan_service import MealPlanService

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing meal planning conversations."""

    def __init__(self, meal_plan_service: MealPlanService):
        self.handler = ConversationHandler(meal_plan_service)
        self.state_handlers = {
            ConversationState.GREETING: self.handler.handle_greeting,
            ConversationState.ASKING_DIETARY_PREFERENCES: self.handler.handle_dietary_preferences,
            ConversationState.ASKING_ALLERGIES: self.handler.handle_allergies,
            ConversationState.ASKING_FITNESS_GOALS: self.handler.handle_fitness_goals,
            ConversationState.ASKING_MEAL_COUNT: self.handler.handle_meal_count,
            ConversationState.ASKING_PLAN_DURATION: self.handler.handle_plan_duration,
            ConversationState.ASKING_COOKING_TIME: self.handler.handle_cooking_time,
            ConversationState.ASKING_CUISINE_PREFERENCES: self.handler.handle_cuisine_preferences,
            ConversationState.CONFIRMING_PREFERENCES: self.handler.handle_confirmation,
            ConversationState.GENERATING_PLAN: self.handler.handle_plan_generation,
            ConversationState.SHOWING_PLAN: self.handler.handle_showing_plan,
            ConversationState.ADJUSTING_MEAL: self.handler.handle_meal_adjustment,
            ConversationState.COMPLETED: self.handler.handle_completed
        }

    def start_conversation(self, user_id: str) -> Conversation:
        """Start a new meal planning conversation."""
        conversation = Conversation(user_id=user_id)

        greeting = ("Hi there! 👋 I'd be happy to help you plan your meals. "
                   "To get started, could you tell me your **dietary preferences or restrictions**? "
                   "(For example: vegan, gluten-free, keto, etc.)")

        conversation.add_message(MessageRole.ASSISTANT, greeting)
        conversation.update_state(ConversationState.ASKING_DIETARY_PREFERENCES)

        return conversation

    def process_message(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """
        Process a user message and return assistant response.

        Returns:
            Tuple of (assistant_message, requires_input, meal_plan_id)
        """
        conversation.add_message(MessageRole.USER, user_message)

        handler = self.state_handlers.get(conversation.state)
        if not handler:
            logger.error(f"No handler for state: {conversation.state}")
            return "I'm sorry, something went wrong. Let's start over.", True, None

        assistant_message, requires_input, meal_plan_id = handler(conversation, user_message)
        conversation.add_message(MessageRole.ASSISTANT, assistant_message)

        return assistant_message, requires_input, meal_plan_id
