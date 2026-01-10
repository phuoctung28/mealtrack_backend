"""
GetMealPlanningSummaryQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.daily_meal import GetMealPlanningSummaryQuery
from src.infra.database.config import ScopedSession
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GetMealPlanningSummaryQuery)
class GetMealPlanningSummaryQueryHandler(EventHandler[GetMealPlanningSummaryQuery, Dict[str, Any]]):
    """Handler for getting meal planning summary."""

    async def handle(self, query: GetMealPlanningSummaryQuery) -> Dict[str, Any]:
        """Get meal planning summary for a profile."""
        db = ScopedSession()

        # Get user profile
        profile = db.query(UserProfile).filter(
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

        tdee_handler = GetUserTdeeQueryHandler()
        tdee_query = GetUserTdeeQuery(user_id=profile.user_id)
        tdee_result = await tdee_handler.handle(tdee_query)

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
