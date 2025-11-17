"""
SaveUserOnboardingCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.user import SaveUserOnboardingCommand
from src.app.events.base import EventHandler, handles
from src.infra.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.user import User
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(SaveUserOnboardingCommand)
class SaveUserOnboardingCommandHandler(EventHandler[SaveUserOnboardingCommand, None]):
    """Handler for saving user onboarding data."""

    def __init__(self, db: Session = None, cache_service: Optional[CacheService] = None):
        self.db = db
        self.cache_service = cache_service

    def set_dependencies(self, db: Session, **kwargs):
        """Set dependencies for dependency injection."""
        self.db = db
        self.cache_service = kwargs.get("cache_service", self.cache_service)

    async def handle(self, command: SaveUserOnboardingCommand) -> None:
        """Save user onboarding data."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Validate input
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
            await self._invalidate_user_profile(command.user_id)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving onboarding data: {str(e)}")
            raise

    async def _invalidate_user_profile(self, user_id: str):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(cache_key)
