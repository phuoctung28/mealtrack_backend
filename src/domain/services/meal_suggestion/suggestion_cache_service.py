"""
Suggestion cache service for caching TDEE and other suggestion-related data.
"""

import logging
from typing import Optional

from src.domain.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class SuggestionCacheService:
    """Cache service for meal suggestions TDEE and related data."""

    def __init__(self, redis_client=None):
        self._redis_client = redis_client

    async def get_cached_tdee(self, user_id: str) -> Optional[float]:
        """Get cached TDEE for user."""
        if not self._redis_client:
            return None

        cache_key, ttl = CacheKeys.user_tdee(user_id)
        try:
            cached = await self._redis_client.get(cache_key)
            if cached:
                logger.debug(f"TDEE cache HIT for user {user_id}")
                return float(cached)
        except Exception as e:
            logger.warning(f"TDEE cache GET failed: {e}")

        return None

    async def set_cached_tdee(self, user_id: str, tdee: float) -> None:
        """Cache TDEE for user."""
        if not self._redis_client:
            return

        cache_key, ttl = CacheKeys.user_tdee(user_id)
        try:
            await self._redis_client.set(cache_key, str(tdee), ttl)
            logger.debug(f"TDEE cached for user {user_id}: {tdee}")
        except Exception as e:
            logger.warning(f"TDEE cache SET failed: {e}")
