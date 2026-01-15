"""
SaveUserOnboardingCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Optional
from uuid import UUID

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.user import SaveUserOnboardingCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.user import UserProfileDomainModel
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(SaveUserOnboardingCommand)
class SaveUserOnboardingCommandHandler(EventHandler[SaveUserOnboardingCommand, None]):
    """Handler for saving user onboarding data."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: SaveUserOnboardingCommand) -> None:
        """Save user onboarding data."""
        # Validate input
        if command.age < 1 or command.age > 120:
            raise ValidationException("Age must be between 1 and 120")

        if command.weight_kg <= 0:
            raise ValidationException("Weight must be greater than 0")

        if command.height_cm <= 0:
            raise ValidationException("Height must be greater than 0")

        # Use provided UoW or create default
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                # Get existing user
                user = uow.users.find_by_id(UUID(command.user_id))
                if not user:
                    raise ResourceNotFoundException(f"User {command.user_id} not found. User must be created before onboarding.")

                # Get or create user profile
                profile = uow.users.get_profile(UUID(command.user_id))

                if not profile:
                    # Create new profile
                    profile = UserProfileDomainModel(
                        user_id=UUID(command.user_id),
                        age=command.age,
                        gender=command.gender,
                        height_cm=command.height_cm,
                        weight_kg=command.weight_kg,
                        body_fat_percentage=command.body_fat_percentage,
                        activity_level=command.activity_level,
                        fitness_goal=command.fitness_goal,
                        meals_per_day=command.meals_per_day,
                        pain_points=command.pain_points,
                        dietary_preferences=command.dietary_preferences
                    )
                else:
                    # Update existing profile
                    profile.age = command.age
                    profile.gender = command.gender
                    profile.height_cm = command.height_cm
                    profile.weight_kg = command.weight_kg
                    profile.body_fat_percentage = command.body_fat_percentage
                    profile.activity_level = command.activity_level
                    profile.fitness_goal = command.fitness_goal
                    profile.meals_per_day = command.meals_per_day
                    profile.pain_points = command.pain_points
                    profile.dietary_preferences = command.dietary_preferences

                # Save profile
                uow.users.update_profile(profile)
                uow.commit()
                await self._invalidate_user_profile(command.user_id)

            except Exception as e:
                uow.rollback()
                logger.error(f"Error saving onboarding data: {str(e)}")
                raise

    async def _invalidate_user_profile(self, user_id: str):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(cache_key)
