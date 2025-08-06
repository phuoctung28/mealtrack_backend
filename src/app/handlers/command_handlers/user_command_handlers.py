"""
Command handlers for user domain - write operations.
"""
import logging
import re
from typing import Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import (
    SaveUserOnboardingCommand
)
from src.app.commands.user.sync_user_command import (
    SyncUserCommand,
    UpdateUserLastAccessedCommand
)
from src.app.events.base import EventHandler, handles
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.tdee import TdeeRequest, Sex, Goal, UnitSystem
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
                "bmr": tdee_result["bmr"],
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


@handles(SyncUserCommand)
class SyncUserCommandHandler(EventHandler[SyncUserCommand, Dict[str, Any]]):
    """Handler for syncing user data from Firebase authentication."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, command: SyncUserCommand) -> Dict[str, Any]:
        """Sync user data from Firebase authentication."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        try:
            # Check if user exists by firebase_uid
            existing_user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()
            
            created = False
            updated = False
            
            if existing_user:
                # Update existing user
                updated = self._update_existing_user(existing_user, command)
                user = existing_user
                logger.info('Updated existing user')
            else:
                # Create new user
                user = self._create_new_user(command)
                created = True
                logger.info('Created new user')
            
            # Commit changes
            self.db.commit()
            self.db.refresh(user)
            
            # Prepare response
            return {
                "user": {
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
                },
                "created": created,
                "updated": updated,
                "message": "User created successfully" if created else "User updated successfully" if updated else "User data up to date"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing user data: {str(e)}")
            raise
    
    def _create_new_user(self, command: SyncUserCommand) -> User:
        """Create a new user from Firebase data."""
        # Generate username if not provided
        username = command.username or self._generate_username(command.email, command.display_name)
        
        # Ensure username is unique
        username = self._ensure_unique_username(username)
        
        # Extract names if not provided
        first_name, last_name = self._extract_names(command.display_name, command.first_name, command.last_name)
        
        # Create new user
        user = User(
            firebase_uid=command.firebase_uid,
            email=command.email,
            username=username,
            password_hash="",  # No password for Firebase users
            first_name=first_name,
            last_name=last_name,
            phone_number=command.phone_number,
            display_name=command.display_name,
            photo_url=command.photo_url,
            provider=command.provider,
            is_active=True,
            onboarding_completed=False,
        )
        
        self.db.add(user)
        return user
    
    def _update_existing_user(self, user: User, command: SyncUserCommand) -> bool:
        """Update existing user with new Firebase data."""
        updated = False
        
        # Update fields that might have changed
        if user.email != command.email:
            user.email = command.email
            updated = True
        
        if user.phone_number != command.phone_number:
            user.phone_number = command.phone_number
            updated = True
        
        if user.display_name != command.display_name:
            user.display_name = command.display_name
            updated = True
        
        if user.photo_url != command.photo_url:
            user.photo_url = command.photo_url
            updated = True
        
        if user.provider != command.provider:
            user.provider = command.provider
            updated = True
        
        # Always update last_accessed
        user.last_accessed = datetime.utcnow()
        updated = True
        
        return updated
    
    def _generate_username(self, email: str, display_name: str = None) -> str:
        """Generate a username from email or display name."""
        if display_name:
            # Use display name, remove spaces and special characters
            username = re.sub(r'[^a-zA-Z0-9]', '', display_name.lower())
        else:
            # Use email prefix
            username = email.split('@')[0]
            username = re.sub(r'[^a-zA-Z0-9]', '', username.lower())
        
        # Ensure minimum length
        if len(username) < 3:
            username = f"user{username}"
        
        # Limit length
        return username[:20]
    
    def _ensure_unique_username(self, base_username: str) -> str:
        """Ensure username is unique by appending numbers if needed."""
        username = base_username
        counter = 1
        
        while self.db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
            # Prevent infinite loop
            if counter > 999:
                username = f"{base_username}{datetime.utcnow.microsecond}"
                break
        
        return username
    
    def _extract_names(self, display_name: str = None, first_name: str = None, last_name: str = None):
        """Extract first and last names from display name or provided names."""
        if first_name and last_name:
            return first_name, last_name
        
        if display_name:
            name_parts = display_name.strip().split()
            if len(name_parts) >= 2:
                return name_parts[0], ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                return name_parts[0], None
        
        return first_name, last_name


@handles(UpdateUserLastAccessedCommand)
class UpdateUserLastAccessedCommandHandler(EventHandler[UpdateUserLastAccessedCommand, Dict[str, Any]]):
    """Handler for updating user's last accessed timestamp."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, command: UpdateUserLastAccessedCommand) -> Dict[str, Any]:
        """Update user's last accessed timestamp."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        try:
            # Find user by firebase_uid
            user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()
            
            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {command.firebase_uid} not found")
            
            # Update last_accessed timestamp
            last_accessed = command.last_accessed or datetime.utcnow
            user.last_accessed = last_accessed
            
            self.db.commit()
            
            return {
                "firebase_uid": command.firebase_uid,
                "updated": True,
                "message": "Last accessed timestamp updated successfully",
                "timestamp": last_accessed
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last accessed: {str(e)}")
            raise

