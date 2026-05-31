"""Command handler for logging a movement entry."""

import logging
from datetime import date, timedelta
from typing import Optional

from src.api.exceptions import ValidationException
from src.app.commands.movement import LogMovementCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.movement import MovementEntry, MovementIntensity
from src.domain.ports.cache_port import CachePort
from src.domain.services.movement_catalog_service import get_activity, get_met
from src.domain.utils.timezone_utils import (
    format_iso_utc,
    noon_utc_for_date,
    resolve_user_timezone_async,
    user_today,
)
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


def _movement_response(entry: MovementEntry) -> dict:
    return {
        "id": entry.id,
        "activity_id": entry.activity_id,
        "activity_name": entry.activity_name,
        "duration_min": entry.duration_min,
        "kcal_burned": entry.kcal_burned,
        "intensity": entry.intensity,
        "source": entry.source,
        "include_in_balance": entry.include_in_balance,
        "logged_at": format_iso_utc(entry.logged_at),
    }


def _validate_log_movement(cmd: LogMovementCommand) -> None:
    if not cmd.activity_name.strip() or len(cmd.activity_name) > 100:
        raise ValidationException("Invalid movement activity", "INVALID_ACTIVITY")
    if cmd.duration_min < 1 or cmd.duration_min > 600:
        raise ValidationException(
            "Duration must be between 1 and 600 minutes", "INVALID_DURATION"
        )
    if cmd.kcal_burned < 0:
        raise ValidationException(
            "Calories burned cannot be negative", "INVALID_KCAL"
        )
    valid_intensities = {item.value for item in MovementIntensity}
    if cmd.intensity not in valid_intensities:
        raise ValidationException("Invalid movement intensity", "INVALID_INTENSITY")
    if cmd.activity_id is not None:
        if get_activity(cmd.activity_id) is None:
            raise ValidationException("Unknown movement activity", "INVALID_ACTIVITY")
        if get_met(cmd.activity_id, cmd.intensity) is None:
            raise ValidationException(
                "Activity does not support movement intensity", "INVALID_INTENSITY"
            )


async def _flush_movement_caches(
    cache: CachePort, user_id: str, log_date: date
) -> None:
    keys_to_delete = [CacheKeys.daily_macros(user_id, log_date)[0]]
    for key in keys_to_delete:
        try:
            await cache.invalidate(key)
        except Exception as exc:
            logger.warning("Cache invalidation failed for key=%s: %s", key, exc)

    activities_pattern = f"user:{user_id}:activities:{log_date.isoformat()}:*"
    try:
        await cache.invalidate_pattern(activities_pattern)
    except Exception as exc:
        logger.warning(
            "Cache pattern invalidation failed for %s: %s", activities_pattern, exc
        )


@handles(LogMovementCommand)
class LogMovementCommandHandler(EventHandler[LogMovementCommand, dict]):
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        cache_service: Optional[CachePort] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, cmd: LogMovementCommand) -> dict:
        _validate_log_movement(cmd)

        async with self.uow as uow:
            user_tz = await resolve_user_timezone_async(
                cmd.user_id, uow, cmd.header_timezone
            )
            log_date = cmd.target_date or user_today(user_tz)
            if log_date > user_today(user_tz) + timedelta(days=1):
                raise ValidationException(
                    "Movement date cannot be more than one day in the future",
                    "INVALID_DATE",
                )

            entry = MovementEntry(
                user_id=cmd.user_id,
                activity_id=cmd.activity_id,
                activity_name=cmd.activity_name,
                duration_min=cmd.duration_min,
                kcal_burned=cmd.kcal_burned,
                intensity=cmd.intensity,
                include_in_balance=cmd.include_in_balance,
                logged_at=noon_utc_for_date(log_date, user_tz),
            )
            saved = await uow.movement_entries.add(entry)
            await uow.commit()

        if self.cache_service:
            await _flush_movement_caches(self.cache_service, cmd.user_id, log_date)

        return _movement_response(saved)
