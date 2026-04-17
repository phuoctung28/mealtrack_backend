"""Handler for updating custom macro targets."""
import logging
from typing import Optional

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.user.update_custom_macros_command import UpdateCustomMacrosCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateCustomMacrosCommand)
class UpdateCustomMacrosCommandHandler(EventHandler[UpdateCustomMacrosCommand, None]):
    """Set or clear custom macro overrides on user profile."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: UpdateCustomMacrosCommand) -> None:
        with UnitOfWork() as uow:
            profile = (
                uow.session.query(UserProfile)
                .filter(
                    UserProfile.user_id == command.user_id,
                    UserProfile.is_current.is_(True),
                )
                .first()
            )

            if not profile:
                raise ResourceNotFoundException(
                    f"Current profile for user {command.user_id} not found"
                )

            # Validate all-or-nothing: all null (reset) or all non-null (set)
            values = [command.protein_g, command.carbs_g, command.fat_g]
            non_null_count = sum(1 for v in values if v is not None)
            if non_null_count not in (0, 3):
                raise ValidationException(
                    "Must set all three macros (protein, carbs, fat) or none to reset"
                )

            profile.custom_protein_g = command.protein_g
            profile.custom_carbs_g = command.carbs_g
            profile.custom_fat_g = command.fat_g
            uow.session.commit()

            action = "cleared" if non_null_count == 0 else "set"
            logger.info(f"Custom macros {action} for user {command.user_id}")

        if self.cache_service:
            tdee_key, _ = CacheKeys.user_tdee(command.user_id)
            await self.cache_service.invalidate(tdee_key)
            profile_key, _ = CacheKeys.user_profile(command.user_id)
            await self.cache_service.invalidate(profile_key)
            # Invalidate both the server's current week and adjacent week to cover
            # timezone skew: server UTC date may differ from user's local date.
            from datetime import date, timedelta
            today = date.today()
            this_week_start = today - timedelta(days=today.weekday())
            next_week_start = this_week_start + timedelta(weeks=1)
            for week_start in (this_week_start, next_week_start):
                weekly_key, _ = CacheKeys.weekly_budget(command.user_id, week_start)
                await self.cache_service.invalidate(weekly_key)
