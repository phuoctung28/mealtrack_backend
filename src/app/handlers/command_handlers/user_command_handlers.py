"""
Command handlers for user domain - write operations.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import (
    SaveUserOnboardingCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.user import (
    UserOnboardedEvent,
    UserProfileUpdatedEvent
)
from src.domain.model.tdee import TdeeRequest, Sex, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.database.models.user import User
from src.infra.database.models.user.profile import UserProfile
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper

logger = logging.getLogger(__name__)


@handles(SaveUserOnboardingCommand)
class SaveUserOnboardingCommandHandler(EventHandler[SaveUserOnboardingCommand, Dict[str, Any]]):
    """Handler for saving user onboarding data."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.tdee_service = TdeeCalculationService()
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, command: SaveUserOnboardingCommand) -> Dict[str, Any]:
        """Save user onboarding data and calculate TDEE."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        # Validate input
        from src.api.exceptions import ValidationException
        
        if command.age < 1 or command.age > 120:
            raise ValidationException("Age must be between 1 and 120")
        
        if command.weight_kg <= 0:
            raise ValidationException("Weight must be greater than 0")
        
        if command.height_cm <= 0:
            raise ValidationException("Height must be greater than 0")
        
        try:
            # Get existing user
            user = self.db.query(User).filter(User.id == command.user_id).first()
            if not user:
                raise ResourceNotFoundException(f"User {command.user_id} not found. User must be created before onboarding.")
            
            # Get or create user profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == command.user_id
            ).first()
            
            if not profile:
                profile = UserProfile(user_id=command.user_id)
            
            # Update profile with personal info
            profile.age = command.age
            profile.gender = command.gender
            profile.height_cm = command.height_cm
            profile.weight_kg = command.weight_kg
            profile.body_fat_percentage = command.body_fat_percentage
            
            # Update goals
            profile.activity_level = command.activity_level
            profile.fitness_goal = command.fitness_goal
            profile.target_weight_kg = command.target_weight_kg
            profile.meals_per_day = command.meals_per_day
            profile.snacks_per_day = command.snacks_per_day
            
            # Update preferences (JSON fields)
            profile.dietary_preferences = command.dietary_preferences or []
            profile.health_conditions = command.health_conditions or []
            profile.allergies = command.allergies or []
            
            # Save profile
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            
            # Calculate TDEE
            tdee_result = self._calculate_tdee_and_macros(profile)
            
            # Prepare response
            return {
                "user_id": command.user_id,
                "profile_created": True,
                "tdee": tdee_result["tdee"],
                "recommended_calories": tdee_result["target_calories"],
                "recommended_macros": tdee_result["macros"]
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving onboarding data: {str(e)}")
            raise
    
    def _calculate_tdee_and_macros(self, profile: UserProfile) -> Dict[str, Any]:
        """Calculate TDEE and macros for a user profile."""
        # Map database values to domain enums
        sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height=profile.height_cm,  # Using cm since unit_system is METRIC
            weight=profile.weight_kg,  # Using kg since unit_system is METRIC
            activity_level=ActivityGoalMapper.map_activity_level(profile.activity_level),
            goal=ActivityGoalMapper.map_goal(profile.fitness_goal),
            body_fat_pct=profile.body_fat_percentage,
            unit_system=UnitSystem.METRIC
        )
        
        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)
        
        # Calculate target calories based on goal
        if tdee_request.goal == Goal.CUTTING:
            target_calories = result.tdee * 0.8
        elif tdee_request.goal == Goal.BULKING:
            target_calories = result.tdee * 1.15
        else:
            target_calories = result.tdee
        
        # Calculate macros
        macros = self.tdee_service.calculate_macros(
            tdee=target_calories,
            goal=tdee_request.goal,
            weight_kg=profile.weight_kg
        )
        
        return {
            "bmr": result.bmr,
            "tdee": result.tdee,
            "target_calories": round(target_calories, 0),
            "macros": {
                "protein": round(macros.protein, 1),
                "carbs": round(macros.carbs, 1),
                "fat": round(macros.fat, 1),
                "calories": round(macros.calories, 1)
            }
        }


