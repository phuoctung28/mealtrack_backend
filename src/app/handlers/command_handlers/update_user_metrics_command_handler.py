"""
Command handler for updating user metrics.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.domain.utils.timezone_utils import utc_now

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException, ValidationException, ConflictException
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.config import ScopedSession
from src.infra.database.models.enums import FitnessGoalEnum, ActivityLevelEnum
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, None]):
    """Handle updating user metrics (weight, activity level, body fat)."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: UpdateUserMetricsCommand) -> None:
        db = ScopedSession()

        # Validate at least one field is provided
        if not any([command.weight_kg, command.activity_level, command.body_fat_percent, command.fitness_goal]):
            raise ValidationException("At least one metric must be provided")

        try:
            # Find existing profile
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == command.user_id
            ).first()

            if not profile:
                raise ResourceNotFoundException(f"User {command.user_id} not found. Profile required to update metrics.")

            # Update provided fields only
            if command.weight_kg is not None:
                if command.weight_kg <= 0:
                    raise ValidationException("Weight must be greater than 0")
                profile.weight_kg = command.weight_kg

            if command.activity_level is not None:
                valid_levels = [e.value for e in ActivityLevelEnum]
                # Also accept legacy aliases
                legacy_aliases = ['sedentary', 'light', 'moderate', 'active', 'extra']
                if command.activity_level not in valid_levels and command.activity_level not in legacy_aliases:
                    raise ValidationException(f"Activity level must be one of: {', '.join(valid_levels)}")
                profile.activity_level = command.activity_level

            if command.body_fat_percent is not None:
                if command.body_fat_percent < 0 or command.body_fat_percent > 70:
                    raise ValidationException("Body fat percentage must be between 0 and 70")
                profile.body_fat_percentage = command.body_fat_percent

            # Handle fitness goal update with cooldown logic
            if command.fitness_goal is not None:
                valid_goals = [e.value for e in FitnessGoalEnum]
                if command.fitness_goal not in valid_goals:
                    raise ValidationException(f"Fitness goal must be one of: {', '.join(valid_goals)}")
                
                # Check if goal is actually changing
                if profile.fitness_goal != command.fitness_goal:
                    # Apply 7-day cooldown unless override is requested
                    if not command.override:
                        # Refresh profile to get latest updated_at from database
                        db.refresh(profile)
                        last_changed = profile.updated_at or profile.created_at
                        if last_changed:
                            # Compare naive datetimes (database stores naive UTC)
                            cooldown_until = last_changed + timedelta(days=7)
                            now = utc_now()
                            if now < cooldown_until:
                                # Format cooldown_until as ISO with Z suffix for UTC
                                cooldown_iso = cooldown_until.isoformat() + "Z"
                                raise ConflictException(
                                    message="Goal was updated recently. Please wait before changing again.",
                                    details={
                                        "cooldown_until": cooldown_iso
                                    }
                                )
                    
                    profile.fitness_goal = command.fitness_goal

            # Ensure this profile is marked as current
            profile.is_current = True

            db.add(profile)
            db.commit()
            db.refresh(profile)
            await self._invalidate_user_profile(command.user_id)

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user metrics: {str(e)}")
            raise

    async def _invalidate_user_profile(self, user_id: str):
        """Invalidate user profile and TDEE cache."""
        if not self.cache_service:
            return
        
        # Invalidate profile cache
        profile_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(profile_key)
        
        # Invalidate TDEE cache (new)
        tdee_key, _ = CacheKeys.user_tdee(user_id)
        await self.cache_service.invalidate(tdee_key)

