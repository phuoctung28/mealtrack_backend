"""
Command handlers for meal plan domain - write operations.
"""
import logging
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.infra.database.models.user.profile import UserProfile

from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    ReplaceMealInPlanCommand
)
from src.app.commands.meal_plan.generate_daily_meal_plan_command import GenerateDailyMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal_plan import (
    ConversationStartedEvent,
    MealPlanGeneratedEvent,
    MealReplacedEvent
)
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.services.meal_plan_conversation_service import MealPlanConversationService
from src.domain.services.meal_plan_service import MealPlanService

logger = logging.getLogger(__name__)


@handles(StartMealPlanConversationCommand)
class StartMealPlanConversationCommandHandler(EventHandler[StartMealPlanConversationCommand, Dict[str, Any]]):
    """Handler for starting meal plan conversations."""
    
    def __init__(self):
        self.conversation_service = MealPlanConversationService()
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
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


@handles(SendConversationMessageCommand)
class SendConversationMessageCommandHandler(EventHandler[SendConversationMessageCommand, Dict[str, Any]]):
    """Handler for sending messages in meal plan conversations."""
    
    def __init__(self):
        self.conversation_service = MealPlanConversationService()
        self.meal_plan_service = MealPlanService()
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
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



@handles(ReplaceMealInPlanCommand)
class ReplaceMealInPlanCommandHandler(EventHandler[ReplaceMealInPlanCommand, Dict[str, Any]]):
    """Handler for replacing meals in plans."""
    
    def __init__(self):
        self.suggestion_service = DailyMealSuggestionService()
        # In-memory storage for demo purposes
        self._meal_plans: Dict[str, Dict[str, Any]] = {}
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
    async def handle(self, command: ReplaceMealInPlanCommand) -> Dict[str, Any]:
        """Replace a meal in a meal plan."""
        # For demo purposes, create a simple replacement
        # In production, this would fetch from database
        raise ValueError(f"Meal plan {command.plan_id} not found - feature not fully implemented")
        
        # Find and replace the meal
        old_meal = None
        for day in meal_plan["days"]:
            if day["date"] == command.date:
                for i, meal in enumerate(day["meals"]):
                    if meal["meal_id"] == command.meal_id:
                        old_meal = meal
                        
                        # Generate replacement meal
                        preferences = {
                            "meal_type": meal["meal_type"],
                            "dietary_preferences": command.dietary_preferences or [],
                            "exclude_ingredients": command.exclude_ingredients or [],
                            "preferred_cuisine": command.preferred_cuisine
                        }
                        
                        # Get user preferences from meal plan
                        user_data = meal_plan.get("user_data", {})
                        new_meal = self.suggestion_service.generate_single_meal(
                            user_data=user_data,
                            meal_type=meal["meal_type"],
                            additional_preferences=preferences
                        )
                        
                        # Replace in the plan
                        day["meals"][i] = self._format_meal(new_meal)
                        
                        result = {
                            "new_meal": day["meals"][i],
                            "events": [
                                MealReplacedEvent(
                                    aggregate_id=command.plan_id,
                                    plan_id=command.plan_id,
                                    old_meal_id=command.meal_id,
                                    new_meal_id=new_meal.id,
                                    date=command.date
                                )
                            ]
                        }
                        
                        logger.info(f"Replaced meal {command.meal_id} with {new_meal.id} in plan {command.plan_id}")
                        return result
        
        raise ValueError(f"Meal {command.meal_id} not found in plan {command.plan_id} for date {command.date}")


@handles(GenerateDailyMealPlanCommand)
class GenerateDailyMealPlanCommandHandler(EventHandler[GenerateDailyMealPlanCommand, Dict[str, Any]]):
    """Handler for generating daily meal plans based on user profile."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.suggestion_service = DailyMealSuggestionService()
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, command: GenerateDailyMealPlanCommand) -> Dict[str, Any]:
        """Generate a daily meal plan based on user profile."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == command.user_id,
            UserProfile.is_current == True
        ).first()
        
        if not profile:
            raise ResourceNotFoundException(
                message="User profile not found",
                details={"user_id": command.user_id}
            )
        
        # Import the command handler to calculate TDEE
        # Calculate TDEE using the proper query handler
        from src.app.handlers.query_handlers.tdee_query_handlers import GetUserTdeeQueryHandler
        tdee_handler = GetUserTdeeQueryHandler(self.db)
        from src.app.queries.tdee import GetUserTdeeQuery
        tdee_query = GetUserTdeeQuery(user_id=profile.user_id)
        tdee_result = await tdee_handler.handle(tdee_query)
        
        # Prepare user data for meal generation
        user_data = {
            'age': profile.age,
            'gender': profile.gender,
            'height': profile.height_cm,
            'weight': profile.weight_kg,
            'activity_level': profile.activity_level or 'moderate',
            'goal': profile.fitness_goal or 'maintenance',
            'dietary_preferences': profile.dietary_preferences or [],
            'health_conditions': profile.health_conditions or [],
            'allergies': profile.allergies or [],
            'target_calories': tdee_result['target_calories'],
            'target_macros': tdee_result['macros']
        }
        
        # Generate daily meal suggestions
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
        
        # Calculate totals
        total_calories = sum(meal.calories for meal in suggested_meals)
        total_protein = sum(meal.protein for meal in suggested_meals)
        total_carbs = sum(meal.carbs for meal in suggested_meals)
        total_fat = sum(meal.fat for meal in suggested_meals)
        
        # Format meals for response
        formatted_meals = []
        for meal in suggested_meals:
            formatted_meals.append({
                "meal_id": meal.meal_id,
                "meal_type": meal.meal_type.value,
                "name": meal.name,
                "description": meal.description,
                "calories": int(meal.calories),
                "protein": meal.protein,
                "carbs": meal.carbs,
                "fat": meal.fat,
                "prep_time": meal.prep_time,
                "cook_time": meal.cook_time,
                "total_time": meal.prep_time + meal.cook_time,
                "ingredients": meal.ingredients,
                "instructions": meal.instructions if hasattr(meal, 'instructions') else [],
                "is_vegetarian": meal.is_vegetarian if hasattr(meal, 'is_vegetarian') else False,
                "is_vegan": meal.is_vegan if hasattr(meal, 'is_vegan') else False,
                "is_gluten_free": meal.is_gluten_free if hasattr(meal, 'is_gluten_free') else False,
                "cuisine_type": meal.cuisine_type if hasattr(meal, 'cuisine_type') else "International"
            })
        
        result = {
            "user_id": command.user_id,
            "date": "today",
            "meals": formatted_meals,
            "total_nutrition": {
                "calories": int(total_calories),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1)
            },
            "target_nutrition": {
                "calories": tdee_result['target_calories'],
                "protein": tdee_result['macros']['protein'],
                "carbs": tdee_result['macros']['carbs'],
                "fat": tdee_result['macros']['fat']
            },
            "user_preferences": {
                "dietary_preferences": profile.dietary_preferences or [],
                "health_conditions": profile.health_conditions or [],
                "allergies": profile.allergies or [],
                "activity_level": profile.activity_level,
                "fitness_goal": profile.fitness_goal,
                "meals_per_day": profile.meals_per_day,
                "snacks_per_day": profile.snacks_per_day
            }
        }
        
        logger.info(f"Generated daily meal plan for user {command.user_id} with {len(formatted_meals)} meals")
        return result