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
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GetUserProfileQuery)
class GetUserProfileQueryHandler(EventHandler[GetUserProfileQuery, Dict[str, Any]]):
    """Handler for getting user profile with TDEE calculation."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
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
        
        # Calculate TDEE
        handler = SaveUserOnboardingCommandHandler(self.db)
        tdee_result = handler._calculate_tdee_and_macros(profile)
        
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