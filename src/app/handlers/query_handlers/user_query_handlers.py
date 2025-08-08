"""
Query handlers for user domain - read operations.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
from src.app.queries.user import (
    GetUserProfileQuery
)
from src.app.queries.user.get_user_by_firebase_uid_query import (
    GetUserByFirebaseUidQuery,
    GetUserOnboardingStatusQuery
)
from src.domain.model import TdeeRequest, UnitSystem, Goal
from src.domain.model.tdee import ActivityLevel, Sex
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user import User
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(GetUserProfileQuery)
class GetUserProfileQueryHandler(EventHandler[GetUserProfileQuery, Dict[str, Any]]):
    """Handler for getting user profile with TDEE calculation."""

    def __init__(self, db: Session = None, tdee_service: TdeeCalculationService = None):
        self.db = db
        self.tdee_service = tdee_service or TdeeCalculationService()

    def set_dependencies(self, db: Session, tdee_service: TdeeCalculationService = None):
        """Set dependencies for dependency injection."""
        self.db = db
        if tdee_service:
            self.tdee_service = tdee_service

    async def handle(self, query: GetUserProfileQuery) -> Dict[str, Any]:
        """Get user profile with calculated TDEE."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == query.user_id
        ).first()

        if not profile:
            raise ResourceNotFoundException(f"Profile for user {query.user_id} not found")

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

        tdee_result = self.tdee_service.calculate_tdee(tdee_request)

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
                "snacks_per_day": profile.snacks_per_day,
                "dietary_preferences": profile.dietary_preferences or [],
                "health_conditions": profile.health_conditions or [],
                "allergies": profile.allergies or [],
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            },
            "tdee": tdee_result
        }


@handles(GetUserByFirebaseUidQuery)
class GetUserByFirebaseUidQueryHandler(EventHandler[GetUserByFirebaseUidQuery, Dict[str, Any]]):
    """Handler for getting user by Firebase UID."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, query: GetUserByFirebaseUidQuery) -> Dict[str, Any]:
        """Get user by Firebase UID."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user by firebase_uid
        user = self.db.query(User).filter(
            User.firebase_uid == query.firebase_uid
        ).first()

        if not user:
            raise ResourceNotFoundException(f"User with Firebase UID {query.firebase_uid} not found")

        return {
            "id": user.id,
            "firebase_uid": user.firebase_uid,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
            "provider": user.provider,
            "is_active": user.is_active,
            "onboarding_completed": user.onboarding_completed,
            "last_accessed": user.last_accessed,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }


@handles(GetUserOnboardingStatusQuery)
class GetUserOnboardingStatusQueryHandler(EventHandler[GetUserOnboardingStatusQuery, Dict[str, Any]]):
    """Handler for getting user's onboarding status by Firebase UID."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, query: GetUserOnboardingStatusQuery) -> Dict[str, Any]:
        """Get user's onboarding status by Firebase UID."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user by firebase_uid
        user = self.db.query(User).filter(
            User.firebase_uid == query.firebase_uid
        ).first()

        if not user:
            raise ResourceNotFoundException(f"User with Firebase UID {query.firebase_uid} not found")

        return {
            "firebase_uid": user.firebase_uid,
            "onboarding_completed": user.onboarding_completed,
            "is_active": user.is_active,
            "last_accessed": user.last_accessed
        }
