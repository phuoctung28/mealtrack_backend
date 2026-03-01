"""
Command handler for updating user metrics.
"""
import logging
from datetime import date
from typing import Optional

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.enums import FitnessGoalEnum, JobTypeEnum
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, None]):
    """Handle updating user metrics (weight, job type, training, body fat)."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: UpdateUserMetricsCommand) -> None:
        # Validate at least one field is provided
        if not any([command.weight_kg, command.job_type, command.training_days_per_week,
                    command.training_minutes_per_session, command.body_fat_percent, command.fitness_goal]):
            raise ValidationException("At least one metric must be provided")

        with UnitOfWork() as uow:
            # Find existing profile - using raw SQL query temporarily until we add get_profile_by_user_id to port
            from src.infra.database.models.user.profile import UserProfile
            profile = uow.session.query(UserProfile).filter(
                UserProfile.user_id == command.user_id
            ).first()

            if not profile:
                raise ResourceNotFoundException(f"User {command.user_id} not found. Profile required to update metrics.")

            # Update provided fields only
            if command.weight_kg is not None:
                if command.weight_kg <= 0:
                    raise ValidationException("Weight must be greater than 0")
                profile.weight_kg = command.weight_kg

            if command.job_type is not None:
                valid_types = [e.value for e in JobTypeEnum]
                if command.job_type not in valid_types:
                    raise ValidationException(f"Job type must be one of: {', '.join(valid_types)}")
                profile.job_type = command.job_type

            if command.training_days_per_week is not None:
                if command.training_days_per_week < 0 or command.training_days_per_week > 7:
                    raise ValidationException("Training days per week must be between 0 and 7")
                profile.training_days_per_week = command.training_days_per_week

            if command.training_minutes_per_session is not None:
                if command.training_minutes_per_session < 15 or command.training_minutes_per_session > 180:
                    raise ValidationException("Training minutes per session must be between 15 and 180")
                profile.training_minutes_per_session = command.training_minutes_per_session

            if command.body_fat_percent is not None:
                if command.body_fat_percent < 0 or command.body_fat_percent > 70:
                    raise ValidationException("Body fat percentage must be between 0 and 70")
                profile.body_fat_percentage = command.body_fat_percent

            # Handle fitness goal update with logging
            if command.fitness_goal is not None:
                valid_goals = [e.value for e in FitnessGoalEnum]
                if command.fitness_goal not in valid_goals:
                    raise ValidationException(f"Fitness goal must be one of: {', '.join(valid_goals)}")

                # Log goal changes for analytics
                if profile.fitness_goal != command.fitness_goal:
                    logger.info(
                        "Fitness goal changed for user %s: %s -> %s",
                        command.user_id,
                        profile.fitness_goal,
                        command.fitness_goal
                    )
                    profile.fitness_goal = command.fitness_goal

            # Ensure this profile is marked as current
            profile.is_current = True

            uow.session.add(profile)
            # UoW auto-commits on exit

        await self._invalidate_user_profile(command.user_id)

    async def _invalidate_user_profile(self, user_id: str):
        """Invalidate user profile, TDEE, and daily macros cache."""
        if not self.cache_service:
            return

        # Invalidate profile cache
        profile_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(profile_key)

        # Invalidate TDEE cache
        tdee_key, _ = CacheKeys.user_tdee(user_id)
        await self.cache_service.invalidate(tdee_key)

        # Invalidate today's daily macros (contains target goals from TDEE)
        daily_macros_key, _ = CacheKeys.daily_macros(user_id, date.today())
        await self.cache_service.invalidate(daily_macros_key)

