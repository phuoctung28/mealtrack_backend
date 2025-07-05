"""
Command handlers for user domain - write operations.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    UpdateUserProfileCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.user import (
    UserOnboardedEvent,
    UserProfileUpdatedEvent
)
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.database.models.user import User
from src.infra.database.models.user.profile import UserProfile

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
        
        try:
            # Get or create user
            user = self.db.query(User).filter(User.id == command.user_id).first()
            if not user:
                user = User(id=command.user_id)
                self.db.add(user)
                self.db.flush()
            
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
                "profile": {
                    "id": profile.id,
                    "user_id": profile.user_id,
                    "age": profile.age,
                    "gender": profile.gender,
                    "height_cm": profile.height_cm,
                    "weight_kg": profile.weight_kg,
                    "body_fat_percentage": profile.body_fat_percentage,
                    "activity_level": profile.activity_level,
                    "fitness_goal": profile.fitness_goal
                },
                "tdee": tdee_result,
                "events": [
                    UserOnboardedEvent(
                        aggregate_id=profile.id,
                        user_id=command.user_id,
                        profile_id=profile.id,
                        tdee=tdee_result["tdee"],
                        target_calories=tdee_result["target_calories"]
                    )
                ]
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving onboarding data: {str(e)}")
            raise
    
    def _calculate_tdee_and_macros(self, profile: UserProfile) -> Dict[str, Any]:
        """Calculate TDEE and macros for a user profile."""
        # Map database values to domain enums
        sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE
        
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "lightly_active": ActivityLevel.LIGHT,
            "moderately_active": ActivityLevel.MODERATE,
            "very_active": ActivityLevel.ACTIVE,
            "extra_active": ActivityLevel.EXTRA
        }
        
        goal_map = {
            "lose_weight": Goal.CUTTING,
            "maintain": Goal.MAINTENANCE,
            "maintenance": Goal.MAINTENANCE,
            "gain_weight": Goal.BULKING,
            "build_muscle": Goal.BULKING
        }
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            activity_level=activity_map.get(profile.activity_level, ActivityLevel.MODERATE),
            goal=goal_map.get(profile.fitness_goal, Goal.MAINTENANCE),
            body_fat_percentage=profile.body_fat_percentage,
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
            "activity_multiplier": result.activity_multiplier,
            "formula_used": result.formula_used,
            "macros": {
                "protein": round(macros.protein, 1),
                "carbs": round(macros.carbs, 1),
                "fat": round(macros.fat, 1),
                "calories": round(macros.calories, 1)
            }
        }


@handles(UpdateUserProfileCommand)
class UpdateUserProfileCommandHandler(EventHandler[UpdateUserProfileCommand, Dict[str, Any]]):
    """Handler for updating user profile."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.tdee_service = TdeeCalculationService()
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, command: UpdateUserProfileCommand) -> Dict[str, Any]:
        """Update user profile with new data."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        try:
            # Get profile
            profile = self.db.query(UserProfile).filter(
                UserProfile.id == command.user_profile_id
            ).first()
            
            if not profile:
                raise ResourceNotFoundException(f"Profile {command.user_profile_id} not found")
            
            # Track old TDEE for event
            old_tdee_result = self._calculate_tdee_and_macros(profile)
            old_tdee = old_tdee_result["tdee"]
            
            # Update profile fields
            updated_fields = []
            for field, value in command.updates.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
                    updated_fields.append(field)
            
            # Save changes
            self.db.commit()
            self.db.refresh(profile)
            
            # Check if TDEE needs recalculation
            tdee_fields = {"age", "height_cm", "weight_kg", "activity_level", "fitness_goal", "body_fat_percentage"}
            new_tdee = None
            new_tdee_result = None
            
            if any(field in updated_fields for field in tdee_fields):
                new_tdee_result = self._calculate_tdee_and_macros(profile)
                new_tdee = new_tdee_result["tdee"]
            
            return {
                "profile": {
                    "id": profile.id,
                    "user_id": profile.user_id,
                    "updated_fields": updated_fields
                },
                "tdee": new_tdee_result if new_tdee_result else old_tdee_result,
                "events": [
                    UserProfileUpdatedEvent(
                        aggregate_id=profile.id,
                        profile_id=profile.id,
                        updated_fields=updated_fields,
                        old_tdee=old_tdee if new_tdee else None,
                        new_tdee=new_tdee
                    )
                ]
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            raise
    
    def _calculate_tdee_and_macros(self, profile: UserProfile) -> Dict[str, Any]:
        """Calculate TDEE and macros for a user profile."""
        # Reuse the method from SaveUserOnboardingCommandHandler
        handler = SaveUserOnboardingCommandHandler(self.db)
        return handler._calculate_tdee_and_macros(profile)