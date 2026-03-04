"""Conversation state handler logic."""
import logging
from typing import Optional, Tuple

from src.domain.model.meal_planning_wizard import Conversation, ConversationContext, ConversationState
from src.domain.services.conversation.conversation_formatter import ConversationFormatter
from src.domain.services.conversation.conversation_parser import ConversationParser

logger = logging.getLogger(__name__)


class ConversationHandler:
    """Handles conversation state transitions and responses."""

    def __init__(self):
        self.parser = ConversationParser()
        self.formatter = ConversationFormatter()

    def handle_greeting(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle initial greeting."""
        response = ("Great! Let's plan your meals. First, could you tell me your "
                   "**dietary preferences or restrictions**? (For example: vegan, gluten-free, keto, etc.)")
        conversation.update_state(ConversationState.ASKING_DIETARY_PREFERENCES)
        return response, True, None

    def handle_dietary_preferences(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle dietary preferences input."""
        preferences = self.parser.parse_dietary_preferences(user_message)
        conversation.context.dietary_preferences = preferences

        response = (f"Got it – {self.formatter.format_list(preferences)}. 👍 "
                   "Next, do you have any **food allergies** I should know about?")
        conversation.update_state(ConversationState.ASKING_ALLERGIES)
        return response, True, None

    def handle_allergies(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle allergies input."""
        allergies = self.parser.parse_allergies(user_message)
        conversation.context.allergies = allergies

        if allergies:
            response = "Perfect. I'll make sure to avoid those. "
        else:
            response = "Perfect. "

        response += "Now, what are your **health or fitness goals**? (For example: weight loss, muscle gain, maintenance...)"
        conversation.update_state(ConversationState.ASKING_FITNESS_GOALS)
        return response, True, None

    def handle_fitness_goals(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle fitness goals input."""
        goal = self.parser.parse_fitness_goal(user_message)
        conversation.context.fitness_goal = goal

        nutrition_focus = {
            FitnessGoal.BULK.value: "I'll make sure to include high-protein options",
            FitnessGoal.CUT.value: "I'll focus on balanced, calorie-controlled meals",
            FitnessGoal.RECOMP.value: "I'll create well-balanced, high-protein meals",
        }

        default_msg = "I'll create appropriate meals for your goal"
        response = (f"Great, thanks! {nutrition_focus.get(goal, default_msg)}. "
                   "How many **meals per day** would you like me to plan?")
        conversation.update_state(ConversationState.ASKING_MEAL_COUNT)
        return response, True, None

    def handle_meal_count(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle meal count input."""
        meals, snacks = self.parser.parse_meal_count(user_message)
        conversation.context.meals_per_day = meals
        conversation.context.snacks_per_day = snacks

        response = (f"Okay. And are we planning for **just one day or a full week** of meals?")
        conversation.update_state(ConversationState.ASKING_PLAN_DURATION)
        return response, True, None

    def handle_plan_duration(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle plan duration input."""
        duration = self.parser.parse_plan_duration(user_message)
        conversation.context.plan_duration = duration

        duration_text = "week-long" if duration == PlanDuration.WEEKLY.value else "daily"
        response = (f"Excellent. I'll prepare a {duration_text} meal plan with {conversation.context.meals_per_day} meals "
                   f"and {conversation.context.snacks_per_day} snacks per day. "
                   "One more thing: how much **time do you usually have to cook** each meal?")
        conversation.update_state(ConversationState.ASKING_COOKING_TIME)
        return response, True, None

    def handle_cooking_time(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle cooking time input."""
        weekday_time, weekend_time = self.parser.parse_cooking_time(user_message)
        conversation.context.cooking_time_weekday = weekday_time
        conversation.context.cooking_time_weekend = weekend_time

        response = ("Understood. I'll keep weeknight recipes quick and use the weekends for anything that takes longer. 🤗 "
                   "Lastly, any specific **ingredients or cuisines you love or want to avoid**?")
        conversation.update_state(ConversationState.ASKING_CUISINE_PREFERENCES)
        return response, True, None

    def handle_cuisine_preferences(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle cuisine preferences input."""
        favorites, dislikes = self.parser.parse_cuisine_preferences(user_message)
        conversation.context.favorite_cuisines = favorites
        conversation.context.disliked_ingredients = dislikes

        summary = self.formatter.build_preferences_summary(conversation.context)
        response = (f"Thanks for the details! 🎉 Let's recap quickly: {summary} Sound good?")
        conversation.update_state(ConversationState.CONFIRMING_PREFERENCES)
        return response, True, None

    def handle_confirmation(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle confirmation."""
        if self.parser.is_affirmative(user_message):
            response = (
                "Perfect! I’ve saved your preferences. "
                "The automated weekly meal-plan generator is currently disabled, "
                "but you can still use daily meal suggestions based on these settings."
            )
            conversation.update_state(ConversationState.COMPLETED)
            return response, False, None
        else:
            response = "No problem! What would you like me to change?"
            return response, True, None

    def handle_showing_plan(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Legacy hook; meal-plan display is currently disabled."""
        response = (
            "Meal plan viewing and adjustment is currently disabled. "
            "You can still generate individual daily meal suggestions from the main app."
        )
        conversation.update_state(ConversationState.COMPLETED)
        return response, False, None

    def handle_meal_adjustment(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Legacy hook; meal adjustment is currently disabled."""
        response = (
            "Adjusting individual meals within a saved plan is currently disabled. "
            "Please request new daily suggestions instead."
        )
        conversation.update_state(ConversationState.COMPLETED)
        return response, False, None

    def handle_completed(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle completed state."""
        response = "Thank you! Feel free to start a new conversation if you need to update your preferences."
        return response, False, None
