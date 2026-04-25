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
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(SaveUserOnboardingCommand)
class SaveUserOnboardingCommandHandler(EventHandler[SaveUserOnboardingCommand, None]):
    """Handler for saving user onboarding data."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CachePort] = None):
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
        uow = self.uow or AsyncUnitOfWork()

        async with uow:
            try:
                # Get existing user
                user = await uow.users.find_by_id(UUID(command.user_id))
                if not user:
                    raise ResourceNotFoundException(f"User {command.user_id} not found. User must be created before onboarding.")

                # Get or create user profile
                profile = await uow.users.get_profile(UUID(command.user_id))

                if not profile:
                    # Create new profile
                    profile = UserProfileDomainModel(
                        user_id=UUID(command.user_id),
                        age=command.age,
                        gender=command.gender,
                        height_cm=command.height_cm,
                        weight_kg=command.weight_kg,
                        body_fat_percentage=command.body_fat_percentage,
                        date_of_birth=command.date_of_birth,
                        target_weight_kg=command.target_weight_kg,
                        job_type=command.job_type,
                        training_days_per_week=command.training_days_per_week,
                        training_minutes_per_session=command.training_minutes_per_session,
                        fitness_goal=command.fitness_goal,
                        meals_per_day=command.meals_per_day,
                        pain_points=command.pain_points or [],
                        dietary_preferences=command.dietary_preferences or [],
                        training_level=command.training_level,
                        referral_sources=command.referral_sources,
                        challenge_duration=command.challenge_duration,
                        training_types=command.training_types,
                    )
                else:
                    # Update existing profile
                    profile.age = command.age
                    profile.gender = command.gender
                    profile.height_cm = command.height_cm
                    profile.weight_kg = command.weight_kg
                    profile.body_fat_percentage = command.body_fat_percentage
                    profile.job_type = command.job_type
                    profile.training_days_per_week = command.training_days_per_week
                    profile.training_minutes_per_session = command.training_minutes_per_session
                    profile.fitness_goal = command.fitness_goal
                    profile.meals_per_day = command.meals_per_day
                    if command.pain_points is not None:
                        profile.pain_points = command.pain_points
                    if command.dietary_preferences is not None:
                        profile.dietary_preferences = command.dietary_preferences
                    profile.training_level = command.training_level
                    profile.date_of_birth = command.date_of_birth
                    profile.target_weight_kg = command.target_weight_kg
                    # Write-once — don't overwrite if already set
                    if command.referral_sources and not profile.referral_sources:
                        profile.referral_sources = command.referral_sources
                    profile.challenge_duration = command.challenge_duration
                    profile.training_types = command.training_types

                # Save custom macro overrides if all three provided
                custom_values = [command.custom_protein_g, command.custom_carbs_g, command.custom_fat_g]
                if all(v is not None for v in custom_values):
                    profile.custom_protein_g = command.custom_protein_g
                    profile.custom_carbs_g = command.custom_carbs_g
                    profile.custom_fat_g = command.custom_fat_g

                # Save profile
                await uow.users.update_profile(profile)
                await uow.commit()
                await self._invalidate_user_profile(command.user_id)

            except Exception as e:
                await uow.rollback()
                logger.error(f"Error saving onboarding data: {str(e)}")
                raise

    async def _invalidate_user_profile(self, user_id: str):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(cache_key)
