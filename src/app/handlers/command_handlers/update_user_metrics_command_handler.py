"""
Command handler for updating user metrics.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException, ValidationException, ConflictException
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, None]):
    """Handle updating user metrics (weight, activity level, body fat)."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        self.db = db

    async def handle(self, command: UpdateUserMetricsCommand) -> None:
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Validate at least one field is provided
        if not any([command.weight_kg, command.activity_level, command.body_fat_percent, command.fitness_goal]):
            raise ValidationException("At least one metric must be provided")

        try:
            # Find existing profile
            profile = self.db.query(UserProfile).filter(
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
                valid_levels = ['sedentary', 'light', 'moderate', 'active', 'extra', 
                              'lightly_active', 'moderately_active', 'very_active', 'extra_active']
                if command.activity_level not in valid_levels:
                    raise ValidationException(f"Activity level must be one of: {', '.join(valid_levels)}")
                profile.activity_level = command.activity_level

            if command.body_fat_percent is not None:
                if command.body_fat_percent < 0 or command.body_fat_percent > 70:
                    raise ValidationException("Body fat percentage must be between 0 and 70")
                profile.body_fat_percentage = command.body_fat_percent

            # Handle fitness goal update with cooldown logic
            if command.fitness_goal is not None:
                valid_goals = ['maintenance', 'cutting', 'bulking']
                if command.fitness_goal not in valid_goals:
                    raise ValidationException(f"Fitness goal must be one of: {', '.join(valid_goals)}")
                
                # Check if goal is actually changing
                if profile.fitness_goal != command.fitness_goal:
                    # Apply 7-day cooldown unless override is requested
                    if not command.override:
                        last_changed = profile.updated_at or profile.created_at
                        if last_changed:
                            cooldown_until = last_changed + timedelta(days=7)
                            if datetime.utcnow() < cooldown_until:
                                raise ConflictException(
                                    message="Goal was updated recently. Please wait before changing again.",
                                    details={
                                        "cooldown_until": cooldown_until.isoformat() + "Z"
                                    }
                                )
                    
                    profile.fitness_goal = command.fitness_goal

            # Ensure this profile is marked as current
            profile.is_current = True

            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user metrics: {str(e)}")
            raise

