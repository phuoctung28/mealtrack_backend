from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class FoodCacheServicePort(ABC):
    """
    Port interface for caching food provider responses.

    Used to reduce external API calls by caching search results and individual
    food detail payloads for a bounded time (TTL).
    """

    @abstractmethod
    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached search results for the given query if available and valid.

        Args:
            query: The exact search string used for provider lookup.

        Returns:
            A list of provider-native search result dictionaries or None if missing/expired.
        """
        pass

    @abstractmethod
    async def cache_search(self, query: str, results: List[Dict[str, Any]], ttl: int = 3600):
        """
        Store search results for a given query with a time-to-live.

        Args:
            query: The exact search string.
            results: Provider-native search results to cache.
            ttl: Time-to-live in seconds (default: 3600).
        """
        pass

    @abstractmethod
    async def get_cached_food(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached food details by provider ID if available and valid.

        Args:
            fdc_id: Provider food identifier (FDC ID).

        Returns:
            Provider-native details dictionary or None if missing/expired.
        """
        pass

    @abstractmethod
    async def cache_food(self, fdc_id: int, food_data: Dict[str, Any], ttl: int = 86400):
        """
        Store food details payload for a given ID with a time-to-live.

        Args:
            fdc_id: Provider food identifier.
            food_data: Provider-native details dictionary to cache.
            ttl: Time-to-live in seconds (default: 86400).
        """
        pass
