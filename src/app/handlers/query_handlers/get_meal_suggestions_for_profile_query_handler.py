"""
GetMealSuggestionsForProfileQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import date
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.daily_meal import GetMealSuggestionsForProfileQuery
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

        # Calculate TDEE using the proper query handler
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
        from src.app.queries.tdee import GetUserTdeeQuery

        tdee_handler = GetUserTdeeQueryHandler(self.db)
        tdee_query = GetUserTdeeQuery(user_id=profile.user_id)
        tdee_result = await tdee_handler.handle(tdee_query)

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
        from src.app.handlers.command_handlers.daily_meal_command_handlers import GenerateDailyMealSuggestionsCommandHandler
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
