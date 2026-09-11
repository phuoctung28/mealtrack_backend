"""Apply meal-write cache deletes to the local Redis used by this API process."""

from __future__ import annotations

import logging
from datetime import date, datetime

from src.domain.cache.cache_invalidation_operations import (
    DELETE_KEY,
    DELETE_PATTERN,
    build_meal_invalidation_operations,
)
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


def _as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


async def apply_meal_write_cache_invalidation(
    cache: CachePort | None,
    user_id: str,
    meal_date: date | datetime,
    old_meal_date: date | datetime | None = None,
) -> None:
    """Delete daily-macros and related keys so Coach cannot keep a stale 0."""
    if cache is None or not user_id:
        return
    dates = {_as_date(meal_date)}
    if old_meal_date is not None:
        dates.add(_as_date(old_meal_date))
    try:
        for day in dates:
            for operation in build_meal_invalidation_operations(user_id, day):
                if operation.get("op") == DELETE_KEY:
                    await cache.invalidate(operation["key"])
                elif operation.get("op") == DELETE_PATTERN:
                    await cache.invalidate_pattern(operation["pattern"])
    except Exception:
        logger.warning(
            "local meal cache invalidation failed user_id=%s",
            user_id,
            exc_info=True,
        )
