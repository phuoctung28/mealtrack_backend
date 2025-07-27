"""
Query handlers for daily meal domain - read operations.
"""
import logging
from datetime import date
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.daily_meal_command_handlers import GenerateDailyMealSuggestionsCommandHandler
from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery
)
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GetMealSuggestionsForProfileQuery)
class GetMealSuggestionsForProfileQueryHandler(EventHandler[GetMealSuggestionsForProfileQuery, Dict[str, Any]]):
    """Handler for getting meal suggestions based on user profile."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.suggestion_service = DailyMealSuggestionService()
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, query: GetMealSuggestionsForProfileQuery) -> Dict[str, Any]:
        """Get meal suggestions for a user profile."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.id == query.user_profile_id
        ).first()
        
        if not profile:
            raise ResourceNotFoundException(
                message="User profile not found",
                details={"user_profile_id": query.user_profile_id}
            )
        
        # Calculate TDEE
        onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
        tdee_result = onboarding_handler._calculate_tdee_and_macros(profile)
        
        # Prepare user data
        user_data = {
            'age': profile.age,
            'gender': profile.gender,
            'height': profile.height_cm,
            'weight': profile.weight_kg,
            'activity_level': profile.activity_level or 'moderate',
            'goal': profile.fitness_goal or 'maintenance',
            'dietary_preferences': profile.dietary_preferences or [],
            'health_conditions': profile.health_conditions or [],
            'target_calories': tdee_result['target_calories'],
            'target_macros': tdee_result['macros']
        }
        
        # Generate suggestions
        suggested_meals = self.suggestion_service.generate_daily_suggestions(user_data)
        
        # Format response
        meal_handler = GenerateDailyMealSuggestionsCommandHandler()
        meals = [meal_handler._format_meal(meal) for meal in suggested_meals]
        
        # Calculate totals
        total_calories = sum(meal.calories for meal in suggested_meals)
        total_protein = sum(meal.protein for meal in suggested_meals)
        total_carbs = sum(meal.carbs for meal in suggested_meals)
        total_fat = sum(meal.fat for meal in suggested_meals)
        
        return {
            "date": date.today().isoformat(),
            "meal_count": len(meals),
            "meals": meals,
            "daily_totals": {
                "calories": round(total_calories, 1),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1)
            },
            "target_calories": tdee_result['target_calories'],
            "target_macros": tdee_result['macros']
        }


@handles(GetSingleMealForProfileQuery)
class GetSingleMealForProfileQueryHandler(EventHandler[GetSingleMealForProfileQuery, Dict[str, Any]]):
    """Handler for getting a single meal suggestion for a profile."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.suggestion_service = DailyMealSuggestionService()
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, query: GetSingleMealForProfileQuery) -> Dict[str, Any]:
        """Get a single meal suggestion for a profile."""
        # Use the profile suggestions handler to get all meals
        profile_handler = GetMealSuggestionsForProfileQueryHandler(self.db)
        all_suggestions = await profile_handler.handle(
            GetMealSuggestionsForProfileQuery(user_profile_id=query.user_profile_id)
        )
        
        # Find the requested meal type
        for meal in all_suggestions["meals"]:
            if meal["meal_type"].lower() == query.meal_type.lower():
                return {
                    "success": True,
                    "meal": meal
                }
        
        raise ValueError(f"No {query.meal_type} suggestion found for profile")


@handles(GetMealPlanningSummaryQuery)
class GetMealPlanningSummaryQueryHandler(EventHandler[GetMealPlanningSummaryQuery, Dict[str, Any]]):
    """Handler for getting meal planning summary."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, query: GetMealPlanningSummaryQuery) -> Dict[str, Any]:
        """Get meal planning summary for a profile."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.id == query.user_profile_id
        ).first()
        
        if not profile:
            raise ResourceNotFoundException(
                message="User profile not found",
                details={"user_profile_id": query.user_profile_id}
            )
        
        # Calculate TDEE
        onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
        tdee_result = onboarding_handler._calculate_tdee_and_macros(profile)
        
        return {
            "profile": {
                "id": profile.id,
                "user_id": profile.user_id,
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "body_fat_percentage": profile.body_fat_percentage,
                "activity_level": profile.activity_level,
                "fitness_goal": profile.fitness_goal,
                "target_weight_kg": profile.target_weight_kg,
                "meals_per_day": profile.meals_per_day,
                "snacks_per_day": profile.snacks_per_day
            },
            "preferences": {
                "dietary_preferences": profile.dietary_preferences or [],
                "health_conditions": profile.health_conditions or [],
                "allergies": profile.allergies or []
            },
            "tdee_calculation": {
                "bmr": tdee_result['bmr'],
                "tdee": tdee_result['tdee'],
                "target_calories": tdee_result['target_calories'],
                "macros": {
                    "protein": tdee_result['macros']['protein'],
                    "carbs": tdee_result['macros']['carbs'],
                    "fat": tdee_result['macros']['fat']
                }
            }
        }