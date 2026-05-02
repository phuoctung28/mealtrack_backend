"""Centralised cache invalidation — handles MealCacheInvalidationRequiredEvent."""

import logging
from datetime import timedelta

from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


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

        week_start = meal_date - timedelta(days=meal_date.weekday())

        daily_key, _ = CacheKeys.daily_macros(user_id, meal_date)
        weekly_key, _ = CacheKeys.weekly_budget(user_id, week_start)
        breakdown_key, _ = CacheKeys.daily_breakdown(user_id, week_start)
        streak_key, _ = CacheKeys.user_streak(user_id)

        # Invalidate specific keys
        for key in (daily_key, weekly_key, breakdown_key, streak_key):
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
