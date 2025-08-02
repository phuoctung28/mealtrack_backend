"""
Command handlers for meal plan domain - write operations.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    ReplaceMealInPlanCommand
)
from src.app.commands.meal_plan.generate_daily_meal_plan_command import GenerateDailyMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal_plan import (
    ConversationStartedEvent,
    MealReplacedEvent
)
from src.domain.model.meal_plan import MealPlan, UserPreferences, DayPlan, DietaryPreference, FitnessGoal, PlanDuration, \
    PlannedMeal
from src.domain.services.meal_plan_conversation_service import MealPlanConversationService
from src.domain.services.meal_plan_orchestration_service import MealPlanOrchestrationService
from src.infra.adapters.meal_generation_service import MealGenerationService
from src.app.handlers.shared.user_profile_service import UserProfileService
from src.app.handlers.shared.meal_plan_persistence_service import MealPlanPersistenceService
from src.infra.database.models.user.profile import UserProfile
from src.infra.repositories.meal_plan_repository import MealPlanRepository

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
        meal_generation_service = MealGenerationService()
        self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)
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
        meal_generation_service = MealGenerationService()
        self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)
        self.user_profile_service = UserProfileService(db) if db else None
        self.persistence_service = MealPlanPersistenceService(db) if db else None
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
        self.user_profile_service = UserProfileService(db)
        self.persistence_service = MealPlanPersistenceService(db)
    
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
        from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
        onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
        tdee_result = onboarding_handler._calculate_tdee_and_macros(profile)
        
        # Get user profile data using shared service
        user_data = self.user_profile_service.get_user_profile_or_defaults(command.user_id)
        user_data['user_id'] = command.user_id
        
        # Generate daily meal plan using orchestration service
        result = self.orchestration_service.generate_daily_plan(user_data)
        
        logger.info(f"Generated daily meal plan for user {command.user_id} with {len(result['meals'])} meals")
        
        # Save to database using shared service
        if self.persistence_service:
            user_preferences = self.user_profile_service.create_user_preferences_from_data(
                user_data, PlanDuration.DAILY
            )
            plan_id = self.persistence_service.save_daily_meal_plan(
                result, user_preferences, command.user_id
            )
            result["plan_id"] = plan_id
            logger.info(f"Saved meal plan {plan_id} to database")
        
        return result