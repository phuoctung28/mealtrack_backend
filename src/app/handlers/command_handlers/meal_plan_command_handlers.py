"""
Command handlers for meal plan domain - write operations.
"""
import logging
from typing import Dict, Any
from uuid import uuid4

from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    GenerateMealPlanCommand,
    ReplaceMealInPlanCommand
)
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
        
        # If conversation is complete, generate meal plan
        if response["state"] == "complete" and response.get("preferences"):
            # Generate meal plan
            handler = GenerateMealPlanCommandHandler()
            meal_plan = handler._generate_simple_meal_plan(
                user_id=response["user_id"],
                preferences=response["preferences"]
            )
            
            result["meal_plan_id"] = meal_plan["id"]
            result["events"].append(
                MealPlanGeneratedEvent(
                    aggregate_id=meal_plan["id"],
                    plan_id=meal_plan["id"],
                    user_id=response["user_id"],
                    days=meal_plan["days"],
                    total_meals=meal_plan["total_meals"]
                )
            )
            
            logger.info(f"Generated meal plan {meal_plan['id']} from conversation {command.conversation_id}")
        
        return result


@handles(GenerateMealPlanCommand)
class GenerateMealPlanCommandHandler(EventHandler[GenerateMealPlanCommand, Dict[str, Any]]):
    """Handler for generating meal plans directly."""
    
    def __init__(self):
        # Using a simplified implementation for now
        self.suggestion_service = DailyMealSuggestionService()
    
    def set_dependencies(self):
        """No external dependencies needed."""
        pass
    
    async def handle(self, command: GenerateMealPlanCommand) -> Dict[str, Any]:
        """Generate a meal plan directly without conversation."""
        # Generate meal plan using daily meal suggestions
        meal_plan = self._generate_simple_meal_plan(
            user_id=command.user_id,
            preferences=command.preferences
        )
        
        result = {
            "meal_plan": meal_plan,
            "events": [
                MealPlanGeneratedEvent(
                    aggregate_id=meal_plan["id"],
                    plan_id=meal_plan["id"],
                    user_id=command.user_id,
                    days=meal_plan["days"],
                    total_meals=meal_plan["total_meals"]
                )
            ]
        }
        
        logger.info(f"Generated meal plan {meal_plan['id']} for user {command.user_id}")
        return result
    
    def _generate_simple_meal_plan(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simple meal plan."""
        from datetime import date, timedelta
        
        plan_id = str(uuid4())
        days = preferences.get("days", 7)
        start_date = date.today()
        
        # Generate days
        meal_days = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            
            # Generate meals for the day
            user_data = {
                "age": preferences.get("age", 30),
                "gender": preferences.get("gender", "male"),
                "height": preferences.get("height", 175),
                "weight": preferences.get("weight", 70),
                "activity_level": preferences.get("activity_level", "moderate"),
                "goal": preferences.get("fitness_goal", "maintenance"),
                "dietary_preferences": preferences.get("dietary_preferences", []),
                "health_conditions": preferences.get("health_conditions", [])
            }
            
            daily_meals = self.suggestion_service.generate_daily_suggestions(user_data)
            
            meal_days.append({
                "date": current_date.isoformat(),
                "meals": [
                    {
                        "meal_id": meal.id,
                        "meal_type": meal.meal_type.value,
                        "name": meal.name,
                        "description": meal.description,
                        "calories": int(meal.calories),
                        "protein": meal.protein,
                        "carbs": meal.carbs,
                        "fat": meal.fat,
                        "prep_time": meal.preparation_time.get("prep", 0) if meal.preparation_time else 0,
                        "ingredients": meal.ingredients
                    }
                    for meal in daily_meals
                ]
            })
        
        return {
            "id": plan_id,
            "user_id": user_id,
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=days-1)).isoformat(),
            "days": days,
            "total_meals": sum(len(day["meals"]) for day in meal_days),
            "preferences": preferences,
            "days": meal_days
        }


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