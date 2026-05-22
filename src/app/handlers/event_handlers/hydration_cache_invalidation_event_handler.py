"""Cache invalidation handler for hydration mutations."""

import logging

from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


@handles(HydrationCacheInvalidationRequiredEvent)
class HydrationCacheInvalidationEventHandler(
    EventHandler[HydrationCacheInvalidationRequiredEvent, None]
):
    """Invalidates all caches affected by a hydration mutation."""

    def __init__(self, cache: CachePort):
        self.cache = cache

    async def handle(self, event: HydrationCacheInvalidationRequiredEvent) -> None:
        user_id = event.user_id
        hydration_date = event.hydration_date

        hydration_key, _ = CacheKeys.daily_hydration(user_id, hydration_date)
        try:
            await self.cache.invalidate(hydration_key)
        except Exception as exc:
            logger.warning("Cache invalidation failed for key=%s: %s", hydration_key, exc)

        activities_pattern = f"user:{user_id}:activities:{hydration_date.isoformat()}:*"
        try:
            await self.cache.invalidate_pattern(activities_pattern)
        except Exception as exc:
            logger.warning("Cache pattern invalidation failed for %s: %s", activities_pattern, exc)
