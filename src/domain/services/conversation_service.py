import logging
import re
from typing import Optional, List, Tuple

from src.domain.model.conversation import (
    Conversation, ConversationContext, ConversationState,
    MessageRole
)
from src.domain.model.meal_planning import (
    UserPreferences, DietaryPreference, FitnessGoal, PlanDuration, MealPlan, MealType
)
from src.domain.services.meal_plan_service import MealPlanService

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing meal planning conversations"""
    
    def __init__(self, meal_plan_service: MealPlanService):
        self.meal_plan_service = meal_plan_service
        self.state_handlers = {
            ConversationState.GREETING: self._handle_greeting,
            ConversationState.ASKING_DIETARY_PREFERENCES: self._handle_dietary_preferences,
            ConversationState.ASKING_ALLERGIES: self._handle_allergies,
            ConversationState.ASKING_FITNESS_GOALS: self._handle_fitness_goals,
            ConversationState.ASKING_MEAL_COUNT: self._handle_meal_count,
            ConversationState.ASKING_PLAN_DURATION: self._handle_plan_duration,
            ConversationState.ASKING_COOKING_TIME: self._handle_cooking_time,
            ConversationState.ASKING_CUISINE_PREFERENCES: self._handle_cuisine_preferences,
            ConversationState.CONFIRMING_PREFERENCES: self._handle_confirmation,
            ConversationState.GENERATING_PLAN: self._handle_plan_generation,
            ConversationState.SHOWING_PLAN: self._handle_showing_plan,
            ConversationState.ADJUSTING_MEAL: self._handle_meal_adjustment,
            ConversationState.COMPLETED: self._handle_completed
        }
    
    def start_conversation(self, user_id: str) -> Conversation:
        """Start a new meal planning conversation"""
        conversation = Conversation(user_id=user_id)
        
        # Add initial greeting
        greeting = ("Hi there! 👋 I'd be happy to help you plan your meals. "
                   "To get started, could you tell me your **dietary preferences or restrictions**? "
                   "(For example: vegan, gluten-free, keto, etc.)")
        
        conversation.add_message(MessageRole.ASSISTANT, greeting)
        conversation.update_state(ConversationState.ASKING_DIETARY_PREFERENCES)
        
        return conversation
    
    def process_message(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """
        Process a user message and return assistant response
        Returns: (assistant_message, requires_input, meal_plan_id)
        """
        # Add user message to conversation
        conversation.add_message(MessageRole.USER, user_message)
        
        # Get handler for current state
        handler = self.state_handlers.get(conversation.state)
        if not handler:
            logger.error(f"No handler for state: {conversation.state}")
            return "I'm sorry, something went wrong. Let's start over.", True, None
        
        # Process message based on current state
        assistant_message, requires_input, meal_plan_id = handler(conversation, user_message)
        
        # Add assistant response
        conversation.add_message(MessageRole.ASSISTANT, assistant_message)
        
        return assistant_message, requires_input, meal_plan_id
    
    def _handle_greeting(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle initial greeting"""
        # This state is only for starting, move to asking dietary preferences
        response = ("Great! Let's plan your meals. First, could you tell me your "
                   "**dietary preferences or restrictions**? (For example: vegan, gluten-free, keto, etc.)")
        conversation.update_state(ConversationState.ASKING_DIETARY_PREFERENCES)
        return response, True, None
    
    def _handle_dietary_preferences(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle dietary preferences input"""
        # Parse dietary preferences from message
        preferences = self._parse_dietary_preferences(user_message)
        conversation.context.dietary_preferences = preferences
        
        response = (f"Got it – {self._format_list(preferences)}. 👍 "
                   "Next, do you have any **food allergies** I should know about?")
        conversation.update_state(ConversationState.ASKING_ALLERGIES)
        return response, True, None
    
    def _handle_allergies(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle allergies input"""
        allergies = self._parse_allergies(user_message)
        conversation.context.allergies = allergies
        
        if allergies:
            response = "Perfect. I'll make sure to avoid those. "
        else:
            response = "Perfect. "
        
        response += "Now, what are your **health or fitness goals**? (For example: weight loss, muscle gain, maintenance...)"
        conversation.update_state(ConversationState.ASKING_FITNESS_GOALS)
        return response, True, None
    
    def _handle_fitness_goals(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle fitness goals input"""
        goal = self._parse_fitness_goal(user_message)
        conversation.context.fitness_goal = goal
        
        nutrition_focus = {
            FitnessGoal.BULKING.value: "I'll make sure to include high-protein options",
            FitnessGoal.CUTTING.value: "I'll focus on balanced, calorie-controlled meals",
            FitnessGoal.MAINTENANCE.value: "I'll create well-balanced meals",
        }
        
        default_msg = "I'll create appropriate meals for your goal"
        response = (f"Great, thanks! {nutrition_focus.get(goal, default_msg)}. "
                   "How many **meals per day** would you like me to plan?")
        conversation.update_state(ConversationState.ASKING_MEAL_COUNT)
        return response, True, None
    
    def _handle_meal_count(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle meal count input"""
        meals, snacks = self._parse_meal_count(user_message)
        conversation.context.meals_per_day = meals
        conversation.context.snacks_per_day = snacks
        
        response = (f"Okay. And are we planning for **just one day or a full week** of meals?")
        conversation.update_state(ConversationState.ASKING_PLAN_DURATION)
        return response, True, None
    
    def _handle_plan_duration(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle plan duration input"""
        duration = self._parse_plan_duration(user_message)
        conversation.context.plan_duration = duration
        
        duration_text = "week-long" if duration == PlanDuration.WEEKLY.value else "daily"
        response = (f"Excellent. I'll prepare a {duration_text} meal plan with {conversation.context.meals_per_day} meals "
                   f"and {conversation.context.snacks_per_day} snacks per day. "
                   "One more thing: how much **time do you usually have to cook** each meal?")
        conversation.update_state(ConversationState.ASKING_COOKING_TIME)
        return response, True, None
    
    def _handle_cooking_time(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle cooking time input"""
        weekday_time, weekend_time = self._parse_cooking_time(user_message)
        conversation.context.cooking_time_weekday = weekday_time
        conversation.context.cooking_time_weekend = weekend_time
        
        response = ("Understood. I'll keep weeknight recipes quick and use the weekends for anything that takes longer. 🤗 "
                   "Lastly, any specific **ingredients or cuisines you love or want to avoid**?")
        conversation.update_state(ConversationState.ASKING_CUISINE_PREFERENCES)
        return response, True, None
    
    def _handle_cuisine_preferences(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle cuisine preferences input"""
        favorites, dislikes = self._parse_cuisine_preferences(user_message)
        conversation.context.favorite_cuisines = favorites
        conversation.context.disliked_ingredients = dislikes
        
        # Build confirmation summary
        summary = self._build_preferences_summary(conversation.context)
        response = (f"Thanks for the details! 🎉 Let's recap quickly: {summary} Sound good?")
        conversation.update_state(ConversationState.CONFIRMING_PREFERENCES)
        return response, True, None
    
    def _handle_confirmation(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle confirmation"""
        if self._is_affirmative(user_message):
            response = "Perfect! Give me a moment to generate your personalized meal plan... 🤖🍳"
            conversation.update_state(ConversationState.GENERATING_PLAN)
            # Trigger plan generation
            return self._handle_plan_generation(conversation, user_message)
        else:
            # Ask what needs to be changed
            response = "No problem! What would you like me to change?"
            # Stay in confirmation state to handle changes
            return response, True, None
    
    def _handle_plan_generation(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Generate the meal plan"""
        try:
            # Create UserPreferences from context
            preferences = self._create_user_preferences(conversation.context)
            
            # Generate meal plan
            meal_plan = self.meal_plan_service.generate_meal_plan(
                user_id=conversation.user_id,
                preferences=preferences
            )
            
            # Store meal plan ID in context
            conversation.context.current_meal_plan = meal_plan.plan_id
            
            # Format response with meal plan
            response = self._format_meal_plan_response(meal_plan)
            conversation.update_state(ConversationState.SHOWING_PLAN)
            
            return response, True, meal_plan.plan_id
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            response = ("I'm sorry, I encountered an error while generating your meal plan. "
                       "Let's try again. What type of meals would you like?")
            conversation.update_state(ConversationState.ASKING_DIETARY_PREFERENCES)
            return response, True, None
    
    def _handle_showing_plan(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle user response after showing plan"""
        if "change" in user_message.lower() or "swap" in user_message.lower() or "replace" in user_message.lower():
            response = ("Sure! Which meal would you like to change? Please specify the day and meal "
                       "(e.g., 'Monday dinner' or 'Tuesday breakfast')")
            conversation.update_state(ConversationState.ADJUSTING_MEAL)
            return response, True, conversation.context.current_meal_plan
        elif self._is_negative(user_message):
            response = "I'm sorry the plan doesn't meet your needs. Would you like to start over with different preferences?"
            return response, True, conversation.context.current_meal_plan
        else:
            response = ("Great! I'm glad you're happy with the meal plan. I'll save this weekly plan for you. "
                       "You can always come back and ask me to regenerate or tweak meals if your preferences "
                       "or schedule change. Enjoy your meals! 🥦💪")
            conversation.update_state(ConversationState.COMPLETED)
            return response, False, conversation.context.current_meal_plan
    
    def _handle_meal_adjustment(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle meal adjustment requests"""
        # This is a simplified version - in production, parse the specific meal to change
        response = ("I'll generate a new option for that meal. "
                   "Would you prefer any specific cuisine or have any additional requirements for this meal?")
        # In production, actually regenerate the meal
        conversation.update_state(ConversationState.SHOWING_PLAN)
        return response, True, conversation.context.current_meal_plan
    
    def _handle_completed(self, conversation: Conversation, user_message: str) -> Tuple[str, bool, Optional[str]]:
        """Handle completed state"""
        response = "Thank you! Feel free to start a new conversation if you need another meal plan."
        return response, False, conversation.context.current_meal_plan
    
    # Parsing helper methods
    def _parse_dietary_preferences(self, message: str) -> List[str]:
        """Parse dietary preferences from user message"""
        message_lower = message.lower()
        preferences = []
        
        preference_keywords = {
            "vegan": ["vegan"],
            "vegetarian": ["vegetarian"],
            "gluten_free": ["gluten-free", "gluten free", "celiac"],
            "keto": ["keto", "ketogenic"],
            "paleo": ["paleo"],
            "low_carb": ["low-carb", "low carb"],
            "dairy_free": ["dairy-free", "dairy free", "lactose"],
            "pescatarian": ["pescatarian", "fish"]
        }
        
        for pref, keywords in preference_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                preferences.append(pref)
        
        if not preferences and ("none" in message_lower or "no" in message_lower):
            preferences.append("none")
        
        return preferences if preferences else ["none"]
    
    def _parse_allergies(self, message: str) -> List[str]:
        """Parse allergies from user message"""
        message_lower = message.lower()
        
        if "no" in message_lower or "none" in message_lower:
            return []
        
        # Common allergens
        allergens = ["nuts", "peanuts", "shellfish", "fish", "eggs", "milk", "dairy",
                    "soy", "wheat", "gluten", "sesame", "tree nuts"]
        
        found_allergies = []
        for allergen in allergens:
            if allergen in message_lower:
                found_allergies.append(allergen)
        
        return found_allergies
    
    def _parse_fitness_goal(self, message: str) -> str:
        """Parse fitness goal from user message"""
        message_lower = message.lower()
        
        if "muscle" in message_lower or "gain" in message_lower or "bulk" in message_lower:
            return FitnessGoal.MUSCLE_GAIN.value
        elif "loss" in message_lower or "lose" in message_lower or "cut" in message_lower:
            return FitnessGoal.WEIGHT_LOSS.value
        elif "maintain" in message_lower or "maintenance" in message_lower:
            return FitnessGoal.MAINTENANCE.value
        else:
            return FitnessGoal.GENERAL_HEALTH.value
    
    def _parse_meal_count(self, message: str) -> Tuple[int, int]:
        """Parse meal and snack count from user message"""
        # Extract numbers from message
        numbers = re.findall(r'\d+', message)
        
        meals = 3  # default
        snacks = 0  # default
        
        if numbers:
            meals = int(numbers[0])
            if len(numbers) > 1:
                snacks = int(numbers[1])
            elif "snack" in message.lower():
                # If they mention snacks but only one number, assume 2 snacks
                snacks = 2
        
        # Reasonable limits
        meals = max(1, min(6, meals))
        snacks = max(0, min(4, snacks))
        
        return meals, snacks
    
    def _parse_plan_duration(self, message: str) -> str:
        """Parse plan duration from user message"""
        message_lower = message.lower()
        
        if "week" in message_lower or "weekly" in message_lower:
            return PlanDuration.WEEKLY.value
        elif "day" in message_lower or "daily" in message_lower:
            return PlanDuration.DAILY.value
        else:
            # Default to weekly
            return PlanDuration.WEEKLY.value
    
    def _parse_cooking_time(self, message: str) -> Tuple[int, int]:
        """Parse cooking time from user message"""
        # Extract numbers
        numbers = re.findall(r'\d+', message)
        
        weekday_time = 30  # default
        weekend_time = 60  # default
        
        if numbers:
            weekday_time = int(numbers[0])
            if len(numbers) > 1:
                weekend_time = int(numbers[1])
            else:
                # If only one time given, assume more time on weekends
                weekend_time = int(weekday_time * 1.5)
        
        return weekday_time, weekend_time
    
    def _parse_cuisine_preferences(self, message: str) -> Tuple[List[str], List[str]]:
        """Parse cuisine preferences and dislikes from user message"""
        message_lower = message.lower()
        
        # Common cuisines
        cuisines = ["italian", "mexican", "asian", "chinese", "japanese", "thai",
                   "indian", "mediterranean", "american", "french", "greek", "spanish"]
        
        favorites = []
        for cuisine in cuisines:
            if cuisine in message_lower:
                favorites.append(cuisine.capitalize())
        
        # Parse dislikes
        dislikes = []
        if "avoid" in message_lower or "don't like" in message_lower or "dislike" in message_lower:
            # Simple parsing - in production, use NLP
            dislike_section = message_lower.split("avoid")[-1] if "avoid" in message_lower else message_lower
            
            # Common ingredients to check
            ingredients = ["tofu", "mushroom", "onion", "garlic", "spicy", "dairy", "egg"]
            for ingredient in ingredients:
                if ingredient in dislike_section:
                    dislikes.append(ingredient)
        
        return favorites, dislikes
    
    def _is_affirmative(self, message: str) -> bool:
        """Check if message is affirmative"""
        affirmative_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "correct", 
                            "right", "sounds good", "perfect", "great"]
        return any(word in message.lower() for word in affirmative_words)
    
    def _is_negative(self, message: str) -> bool:
        """Check if message is negative"""
        negative_words = ["no", "nope", "not", "wrong", "incorrect", "bad"]
        return any(word in message.lower() for word in negative_words)
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list for display"""
        if not items:
            return "none"
        elif len(items) == 1:
            return items[0]
        else:
            return ", ".join(items[:-1]) + f" and {items[-1]}"
    
    def _build_preferences_summary(self, context: ConversationContext) -> str:
        """Build a summary of user preferences"""
        duration = "weekly" if context.plan_duration == PlanDuration.WEEKLY.value else "daily"
        dietary = self._format_list(context.dietary_preferences or ["none"])
        
        summary = (f"You want a {duration}, {dietary} **meal plan** "
                  f"with {context.meals_per_day} meals")
        
        if context.snacks_per_day:
            summary += f" and {context.snacks_per_day} snacks"
        
        summary += f" per day. "
        
        if context.fitness_goal:
            summary += f"Your goal is {context.fitness_goal.replace('_', ' ')}. "
        
        summary += (f"You have ~{context.cooking_time_weekday} minutes to cook on weeknights, "
                   f"more on weekends.")
        
        if context.favorite_cuisines:
            summary += f" You enjoy {self._format_list(context.favorite_cuisines)} foods"
        
        if context.disliked_ingredients:
            summary += f", and we'll avoid {self._format_list(context.disliked_ingredients)}"
        
        if context.allergies:
            summary += f". You're allergic to {self._format_list(context.allergies)}"
        
        summary += "."
        
        return summary
    
    def _create_user_preferences(self, context: ConversationContext) -> UserPreferences:
        """Create UserPreferences from conversation context"""
        # Convert string preferences to enum values
        dietary_prefs = []
        for pref in context.dietary_preferences or ["none"]:
            try:
                dietary_prefs.append(DietaryPreference(pref))
            except ValueError:
                dietary_prefs.append(DietaryPreference.NONE)
        
        fitness_goal = FitnessGoal(context.fitness_goal or "general_health")
        plan_duration = PlanDuration(context.plan_duration or "weekly")
        
        return UserPreferences(
            dietary_preferences=dietary_prefs,
            allergies=context.allergies or [],
            fitness_goal=fitness_goal,
            meals_per_day=context.meals_per_day or 3,
            snacks_per_day=context.snacks_per_day or 0,
            cooking_time_weekday=context.cooking_time_weekday or 30,
            cooking_time_weekend=context.cooking_time_weekend or 60,
            favorite_cuisines=context.favorite_cuisines or [],
            disliked_ingredients=context.disliked_ingredients or [],
            plan_duration=plan_duration
        )
    
    def _format_meal_plan_response(self, meal_plan: MealPlan) -> str:
        """Format meal plan for display"""
        response = "Here's your **meal plan for the week**. I've organized it by day, with each meal tailored to your preferences and goals:\n\n"
        
        for day in meal_plan.days[:2]:  # Show first 2 days as example
            response += f"**{day.date.strftime('%A')}**\n\n"
            
            for meal in day.meals:
                response += f"* **{meal.meal_type.value.capitalize()}:** {meal.name} – *{meal.description}*"
                if meal.meal_type != MealType.SNACK:
                    response += f" (prep time ~{meal.total_time} min)"
                response += ".\n"
            
            response += "\n"
        
        response += ("*(...and similar meal listings for the rest of the week, "
                    "each meeting your dietary requirements and fitness goals...)*\n\n")
        
        response += ("I've kept the recipes **simple for busy weekdays** and included some of your favorite flavors "
                    "throughout the week. Each meal is tailored to your requirements and goals. "
                    "Let me know if anything doesn't look right or if you'd like to **adjust any specific meal**! 😊")
        
        return response