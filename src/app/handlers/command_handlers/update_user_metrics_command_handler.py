"""
Command handler for updating user metrics.
"""

import logging

from src.domain.exceptions.base import ResourceNotFoundException, ValidationException
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.common.enums import FitnessGoal, JobType, TrainingLevel
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)

_VALID_JOB_TYPES = {e.value for e in JobType}
_VALID_FITNESS_GOALS = {e.value for e in FitnessGoal}
_VALID_TRAINING_LEVELS = {e.value for e in TrainingLevel}


@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, None]):
    """Handle updating user metrics (weight, job type, training, body fat)."""

    def __init__(self, uow: AsyncUnitOfWorkPort, cache_service: CachePort | None = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: UpdateUserMetricsCommand) -> None:
        # Validate at least one field is provided
        if not any(
            [
                command.weight_kg,
                command.job_type,
                command.training_days_per_week,
                command.training_minutes_per_session,
                command.body_fat_percent,
                command.fitness_goal,
                command.training_level,
                command.target_weight_kg,
                command.goal_start_weight_kg,
                command.goal_started_at,
                command.daily_water_goal_ml,
                command.reset_water_goal,
            ]
        ):
            raise ValidationException("At least one metric must be provided")

        async with self.uow as uow:
            profile = await uow.users.get_profile(command.user_id)

            if not profile:
                raise ResourceNotFoundException(
                    f"User {command.user_id} not found. Profile required to update metrics."
                )

            # Update provided fields only
            if command.weight_kg is not None:
                if command.weight_kg <= 0:
                    raise ValidationException("Weight must be greater than 0")
                profile.weight_kg = command.weight_kg

            if command.job_type is not None:
                if command.job_type not in _VALID_JOB_TYPES:
                    raise ValidationException(
                        f"Job type must be one of: {', '.join(sorted(_VALID_JOB_TYPES))}"
                    )
                profile.job_type = command.job_type

            if command.training_days_per_week is not None:
                if (
                    command.training_days_per_week < 0
                    or command.training_days_per_week > 7
                ):
                    raise ValidationException(
                        "Training days per week must be between 0 and 7"
                    )
                profile.training_days_per_week = command.training_days_per_week

            if command.training_minutes_per_session is not None:
                if (
                    command.training_minutes_per_session < 15
                    or command.training_minutes_per_session > 180
                ):
                    raise ValidationException(
                        "Training minutes per session must be between 15 and 180"
                    )
                profile.training_minutes_per_session = (
                    command.training_minutes_per_session
                )

            if command.body_fat_percent is not None:
                if command.body_fat_percent < 0 or command.body_fat_percent > 70:
                    raise ValidationException(
                        "Body fat percentage must be between 0 and 70"
                    )
                profile.body_fat_percentage = command.body_fat_percent

            # Handle fitness goal update with logging
            if command.fitness_goal is not None:
                if command.fitness_goal not in _VALID_FITNESS_GOALS:
                    raise ValidationException(
                        f"Fitness goal must be one of: {', '.join(sorted(_VALID_FITNESS_GOALS))}"
                    )

                # Log goal changes for analytics
                if profile.fitness_goal != command.fitness_goal:
                    logger.info(
                        "Fitness goal changed for user %s: %s -> %s",
                        command.user_id,
                        profile.fitness_goal,
                        command.fitness_goal,
                    )
                    profile.fitness_goal = command.fitness_goal

            # Handle training level update
            if command.training_level is not None:
                if command.training_level not in _VALID_TRAINING_LEVELS:
                    raise ValidationException(
                        f"Training level must be one of: {sorted(_VALID_TRAINING_LEVELS)}"
                    )
                profile.training_level = command.training_level

            # Handle target weight update
            if command.target_weight_kg is not None:
                if command.target_weight_kg <= 0:
                    raise ValidationException("Target weight must be greater than 0")
                logger.info(
                    f"Updating target_weight_kg for user {command.user_id}: "
                    f"{profile.target_weight_kg} -> {command.target_weight_kg}"
                )
                profile.target_weight_kg = command.target_weight_kg

            # Handle goal start fields (for progress tracking reset)
            if command.goal_start_weight_kg is not None:
                if command.goal_start_weight_kg <= 0:
                    raise ValidationException(
                        "Goal start weight must be greater than 0"
                    )
                logger.info(
                    f"Updating goal_start_weight_kg for user {command.user_id}: "
                    f"{profile.goal_start_weight_kg} -> {command.goal_start_weight_kg}"
                )
                profile.goal_start_weight_kg = command.goal_start_weight_kg

            if command.goal_started_at is not None:
                logger.info(
                    f"Updating goal_started_at for user {command.user_id}: "
                    f"{profile.goal_started_at} -> {command.goal_started_at}"
                )
                profile.goal_started_at = command.goal_started_at

            if command.reset_water_goal:
                profile.daily_water_goal_ml = None
            elif command.daily_water_goal_ml is not None:
                if command.daily_water_goal_ml <= 0:
                    raise ValidationException("Daily water goal must be greater than 0")
                profile.daily_water_goal_ml = command.daily_water_goal_ml

            # Ensure this profile is marked as current
            profile.is_current = True

            await uow.users.update_profile(profile)

        await self._invalidate_user_profile(command.user_id)

    async def _invalidate_user_profile(self, user_id: str):
        """Invalidate user profile, TDEE, metrics, and ALL daily macros cache."""
        if not self.cache_service:
            return

        # Invalidate profile cache
        profile_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(profile_key)

        # Invalidate TDEE cache
        tdee_key, _ = CacheKeys.user_tdee(user_id)
        await self.cache_service.invalidate(tdee_key)

        # Invalidate user metrics cache
        metrics_key, _ = CacheKeys.user_metrics(user_id)
        await self.cache_service.invalidate(metrics_key)

        # Invalidate ALL cached daily macros for this user (not just today)
        # TDEE changes affect targets for all dates
        macros_pattern = f"user:{user_id}:macros:*"
        try:
            await self.cache_service.invalidate_pattern(macros_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate macros pattern for user {user_id}: {e}")

        # Invalidate ALL weekly budgets for this user
        # TDEE changes affect weekly targets
        weekly_pattern = CacheKeys.weekly_budget_user_pattern(user_id)
        try:
            await self.cache_service.invalidate_pattern(weekly_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate weekly budget pattern for user {user_id}: {e}")

        hydration_pattern = f"user:{user_id}:hydration:*"
        try:
            await self.cache_service.invalidate_pattern(hydration_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate hydration pattern for user {user_id}: {e}")

        weekly_hydration_pattern = f"user:{user_id}:hydration_weekly:*"
        try:
            await self.cache_service.invalidate_pattern(weekly_hydration_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate weekly hydration pattern for user {user_id}: {e}")
