"""Centralised cache invalidation — handles MealCacheInvalidationRequiredEvent."""

import logging
from datetime import date, timedelta

from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


def _get_week_start(d: date) -> date:
    """Get Monday of the week containing the given date."""
    return d - timedelta(days=d.weekday())


@handles(MealCacheInvalidationRequiredEvent)
class CacheInvalidationEventHandler(
    EventHandler[MealCacheInvalidationRequiredEvent, None]
):
    """Invalidates all caches affected by a meal mutation."""

    def __init__(self, cache: CachePort):
        self.cache = cache

    async def handle(self, event: MealCacheInvalidationRequiredEvent) -> None:
        user_id = event.user_id
        meal_date = event.meal_date

        meal_week_start = _get_week_start(meal_date)
        current_week_start = _get_week_start(date.today())

        daily_key, _ = CacheKeys.daily_macros(user_id, meal_date)
        weekly_key, _ = CacheKeys.weekly_budget(user_id, meal_week_start)
        breakdown_key, _ = CacheKeys.daily_breakdown(user_id, meal_week_start)
        streak_key, _ = CacheKeys.user_streak(user_id)

        keys_to_invalidate = [daily_key, weekly_key, breakdown_key, streak_key]

        # If meal is in a different week than current, also invalidate current week
        # This handles backdated meal logging
        if meal_week_start != current_week_start:
            current_weekly_key, _ = CacheKeys.weekly_budget(user_id, current_week_start)
            current_breakdown_key, _ = CacheKeys.daily_breakdown(user_id, current_week_start)
            keys_to_invalidate.extend([current_weekly_key, current_breakdown_key])
            logger.debug(
                "Meal in different week: invalidating both meal_week=%s and current_week=%s",
                meal_week_start, current_week_start
            )

        # Invalidate specific keys
        for key in keys_to_invalidate:
            try:
                await self.cache.invalidate(key)
            except Exception as exc:
                logger.warning("Cache invalidation failed for key=%s: %s", key, exc)

        # Invalidate all language variants of daily activities using pattern
        activities_pattern = f"user:{user_id}:activities:{meal_date.isoformat()}:*"
        try:
            await self.cache.invalidate_pattern(activities_pattern)
        except Exception as exc:
            logger.warning("Cache pattern invalidation failed for %s: %s", activities_pattern, exc)
