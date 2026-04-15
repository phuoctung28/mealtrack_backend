"""
Food image search service with in-memory LRU cache.
Search chain: adapter list (injected) → first hit wins.
Cache: 7-day TTL, max 5000 entries with LRU eviction.
Validation: reject images whose alt text has zero food-keyword overlap with query.
"""
import logging
import re
import time
from collections import OrderedDict
from typing import List, Optional

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
CACHE_MAX_ENTRIES = 5_000

# Words too generic to be useful for matching
_STOP_WORDS = frozenset({
    "a", "an", "the", "with", "and", "or", "of", "in", "on", "for",
    "style", "type", "dish", "food", "meal", "recipe", "plate",
    "fresh", "delicious", "served", "background", "white", "black",
    "wooden", "table", "bowl", "top", "view", "close",
})

# Food-related words that confirm an image is about food
_FOOD_SIGNALS = frozenset({
    "chicken", "beef", "pork", "fish", "shrimp", "salmon", "tuna",
    "rice", "pasta", "noodle", "bread", "salad", "soup", "steak",
    "grilled", "roasted", "fried", "baked", "steamed", "sauteed",
    "vegetable", "tomato", "potato", "onion", "garlic", "pepper",
    "cheese", "egg", "butter", "cream", "sauce", "curry",
    "caesar", "mediterranean", "thai", "mexican", "italian",
})


class FoodImageSearchService:
    """
    Orchestrates food image search with adapter fallback chain.
    Uses an LRU in-memory cache keyed by normalized query.
    """

    def __init__(self, adapters: List[FoodImageSearchPort]):
        self._adapters = adapters
        self._cache: OrderedDict = OrderedDict()

    async def search_food_image(
        self,
        query: str,
        ingredients: Optional[List[str]] = None,
    ) -> Optional[FoodImageResult]:
        """Return a validated food image, or None (mobile falls back to emoji).

        Args:
            query: Food name in English for best search results.
            ingredients: English ingredient names for fallback search.
        """
        key = self._normalize(query)

        cached = self._cache.get(key)
        if cached is not None:
            result, expires_ts = cached
            if time.time() < expires_ts:
                self._cache.move_to_end(key)
                return result
            else:
                del self._cache[key]

        result = await self._search_with_validation(query)

        self._evict_if_needed()
        self._cache[key] = (result, time.time() + CACHE_TTL_SECONDS)
        self._cache.move_to_end(key)

        return result

    async def _search_with_validation(self, query: str) -> Optional[FoodImageResult]:
        """Search adapters with validation. Returns None if no confident match."""
        result = await self._try_adapters_validated(query)
        if result:
            return result

        # Fallback: simplify query to core food words only
        simple = _simplify_food_query(query)
        if simple and simple != query.lower():
            logger.info(f"Image fallback: '{query}' → '{simple}'")
            result = await self._try_adapters_validated(simple)
            if result:
                return result

        logger.info(f"No confident image for '{query}', falling back to emoji")
        return None

    async def _try_adapters_validated(self, query: str) -> Optional[FoodImageResult]:
        """Try each adapter, return first result that passes validation."""
        for adapter in self._adapters:
            try:
                result = await adapter.search(query)
                if result is not None and _validate_food_image(query, result):
                    return result
            except Exception as e:
                logger.warning(f"Image adapter {adapter.__class__.__name__} error: {e}")
        return None

    @staticmethod
    def _normalize(query: str) -> str:
        return query.strip().lower()

    def _evict_if_needed(self) -> None:
        while len(self._cache) >= CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)


def _validate_food_image(query: str, result: FoodImageResult) -> bool:
    """Validate image is food-related and relevant to the query.

    Strategy: check that alt text contains at least one food keyword
    from either the query or the global food signals list.
    This catches obvious mismatches (buildings, landscapes) while
    trusting the search API's relevance for food-on-food matches.
    """
    alt = result.alt_text or ""
    if not alt:
        # No alt text — trust the search API
        return True

    alt_words = _extract_words(alt)
    query_words = _extract_words(query)

    # Must have at least one query keyword in alt text
    query_overlap = query_words & alt_words
    if query_overlap:
        return True

    # Or: alt text must mention food-related words (it's at least a food photo)
    food_overlap = alt_words & _FOOD_SIGNALS
    if food_overlap:
        logger.debug(
            f"Image accepted via food signals: query='{query}' | "
            f"signals={food_overlap}"
        )
        return True

    logger.info(
        f"Image rejected: no food overlap | "
        f"query_words={query_words} | alt_words={alt_words}"
    )
    return False


def _simplify_food_query(query: str) -> str:
    """Extract core food words from a meal name for simpler search.

    E.g. 'Honey Garlic Glazed Chicken Breast' → 'honey garlic chicken'
    """
    words = _extract_words(query)
    food_words = words & _FOOD_SIGNALS
    remaining = words - _STOP_WORDS - _FOOD_SIGNALS
    # Keep food signals + up to 2 descriptive words
    result_words = food_words | set(list(remaining)[:2])
    return " ".join(sorted(result_words)) if result_words else query.lower()


def _extract_words(text: str) -> set:
    """Extract lowercase words, strip punctuation."""
    return set(re.findall(r'[a-zA-Z]{2,}', text.lower()))
