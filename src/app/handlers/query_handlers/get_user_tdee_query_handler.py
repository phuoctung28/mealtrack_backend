"""
GetUserTdeeQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.tdee import GetUserTdeeQuery
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GetUserTdeeQuery)
class GetUserTdeeQueryHandler(EventHandler[GetUserTdeeQuery, Dict[str, Any]]):
    """Handler for getting user's TDEE calculation."""

    def __init__(self, db: Session = None, tdee_service: TdeeCalculationService = None):
        self.db = db
        self.tdee_service = tdee_service or TdeeCalculationService()

    def set_dependencies(self, db: Session, tdee_service: TdeeCalculationService = None):
        """Set dependencies for dependency injection."""
        self.db = db
        if tdee_service:
            self.tdee_service = tdee_service

    async def handle(self, query: GetUserTdeeQuery) -> Dict[str, Any]:
        """Get user's TDEE calculation based on current profile."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get current user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == query.user_id,
            UserProfile.is_current == True
        ).first()

        if not profile:
            raise ResourceNotFoundException(f"Current profile for user {query.user_id} not found")

        # Map profile data to TDEE request
        sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE

        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "light": ActivityLevel.LIGHT,
            "moderate": ActivityLevel.MODERATE,
            "active": ActivityLevel.ACTIVE,
            "extra": ActivityLevel.EXTRA
        }

        goal_map = {
            "maintenance": Goal.MAINTENANCE,
            "cutting": Goal.CUTTING,
            "bulking": Goal.BULKING
        }

        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height=profile.height_cm,
            weight=profile.weight_kg,
            activity_level=activity_map.get(profile.activity_level, ActivityLevel.MODERATE),
            goal=goal_map.get(profile.fitness_goal, Goal.MAINTENANCE),
            body_fat_pct=profile.body_fat_percentage,
            unit_system=UnitSystem.METRIC
        )

        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)
        # Determine activity multiplier for response
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.EXTRA: 1.9
        }
        activity_multiplier = activity_multipliers.get(tdee_request.activity_level, 1.55)

        # Determine formula used
        formula_used = "Katch-McArdle" if tdee_request.body_fat_pct is not None else "Mifflin-St Jeor"

        return {
            "user_id": query.user_id,
            "bmr": result.bmr,
            "tdee": result.tdee,
            "target_calories": round(result.macros.calories, 0),
            "activity_multiplier": activity_multiplier,
            "formula_used": formula_used,
            "macros": {
                "protein": round(result.macros.protein, 1),
                "carbs": round(result.macros.carbs, 1),
                "fat": round(result.macros.fat, 1),
                "calories": round(result.macros.calories, 1)
            },
            "profile_data": {
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "activity_level": profile.activity_level,
                "fitness_goal": profile.fitness_goal,
                "body_fat_percentage": profile.body_fat_percentage
            }
        }
