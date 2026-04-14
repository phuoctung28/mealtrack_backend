"""
Food image search service with in-memory LRU cache.
Search chain: adapter list (injected) → first hit wins.
Cache: 7-day TTL, max 5000 entries with LRU eviction.
Confidence scoring: measures how well the image describes the meal name.
"""
import logging
import time
from collections import OrderedDict
from typing import List, Optional

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort
from src.domain.services.meal_discovery import extract_words

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
CACHE_MAX_ENTRIES = 5_000

# Minimum confidence to accept an image (below this → emoji fallback)
MIN_ACCEPT_CONFIDENCE = 0.3

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
    "tofu", "lamb", "duck", "crab", "lobster", "oyster", "sushi",
    "ramen", "pho", "taco", "burrito", "pizza", "burger",
    "pancake", "waffle", "omelette", "sandwich", "wrap",
    "smoothie", "juice", "yogurt", "granola", "cereal",
    "avocado", "broccoli", "spinach", "kale", "mushroom",
    "lentil", "bean", "chickpea", "hummus", "falafel",
})

# Non-food visual signals — strong indicator the image is wrong
_NEGATIVE_SIGNALS = frozenset({
    "building", "architecture", "skyline", "city", "street",
    "car", "vehicle", "mountain", "landscape", "sunset",
    "portrait", "selfie", "office", "computer", "phone",
    "abstract", "pattern", "texture", "wallpaper",
})


class FoodImageSearchService:
    """
    Orchestrates food image search with adapter fallback chain.
    Uses an LRU in-memory cache keyed by normalized query.
    Scores each image on how well it describes the queried meal name.
    """

    def __init__(
        self,
        adapters: List[FoodImageSearchPort],
        web_validator: Optional["WebSearchImageValidator"] = None,
    ):
        self._adapters = adapters
        self._cache: OrderedDict = OrderedDict()
        self._web_validator = web_validator

    async def search_food_image(
        self,
        query: str,
        ingredients: Optional[List[str]] = None,
    ) -> Optional[FoodImageResult]:
        """Return a scored food image, or None (mobile falls back to emoji).

        The returned FoodImageResult.confidence indicates how well the
        image describes the meal name (0.0–1.0). Mobile uses this to
        decide whether to show the image (>=0.8) or fall back to emoji.
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

        result = await self._search_with_scoring(query)

        self._evict_if_needed()
        self._cache[key] = (result, time.time() + CACHE_TTL_SECONDS)
        self._cache.move_to_end(key)

        return result

    async def _search_with_scoring(self, query: str) -> Optional[FoodImageResult]:
        """Search adapters, score each candidate, return best above threshold."""
        result = await self._try_adapters_scored(query)
        if result:
            return result

        # Fallback: simplify query to core food words only
        simple = _simplify_food_query(query)
        if simple and simple != query.lower():
            logger.info(f"Image fallback: '{query}' → '{simple}'")
            result = await self._try_adapters_scored(simple)
            if result:
                return result

        logger.info(f"No confident image for '{query}', falling back to emoji")
        return None

    async def _try_adapters_scored(self, query: str) -> Optional[FoodImageResult]:
        """Try each adapter, score results, return best above threshold."""
        best: Optional[FoodImageResult] = None
        best_score = 0.0

        for adapter in self._adapters:
            try:
                result = await adapter.search(query)
                if result is None:
                    continue

                score = _score_image_match(query, result)
                if score < MIN_ACCEPT_CONFIDENCE:
                    continue

                # Web search can boost or penalize the score
                if self._web_validator:
                    web_score = await self._web_validator.score(query, result)
                    # Blend: 60% keyword score + 40% web score
                    score = score * 0.6 + web_score * 0.4

                result.confidence = round(score, 2)

                if score > best_score:
                    best = result
                    best_score = score

                # Early exit if we already have a strong match
                if best_score >= 0.9:
                    break
            except Exception as e:
                logger.warning(f"Image adapter {adapter.__class__.__name__} error: {e}")

        if best:
            logger.debug(
                f"Image selected: query='{query}' | confidence={best.confidence}"
            )
        return best

    @staticmethod
    def _normalize(query: str) -> str:
        return query.strip().lower()

    def _evict_if_needed(self) -> None:
        while len(self._cache) >= CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)


def _score_image_match(query: str, result: FoodImageResult) -> float:
    """Score how well the image describes the meal name (0.0–1.0).

    Scoring tiers:
    - 0.0: Non-food image (buildings, cars, etc.)
    - 0.3: No alt text — trust the search API blindly
    - 0.5: Alt text has generic food words but no query overlap
    - 0.7: Alt text has some query keywords (partial match)
    - 0.9: Alt text has most query keywords (strong match)
    - 1.0: Alt text contains all meaningful query words (exact match)
    """
    alt = result.alt_text or ""
    if not alt:
        # No alt text — moderate trust in the search API
        return 0.3

    alt_words = extract_words(alt)
    query_words = extract_words(query) - _STOP_WORDS

    if not query_words:
        return 0.3

    # Hard reject: non-food signals with no food words
    negative_overlap = alt_words & _NEGATIVE_SIGNALS
    if negative_overlap and not (alt_words & _FOOD_SIGNALS):
        logger.info(
            f"Image scored 0.0: non-food signals={negative_overlap} | query='{query}'"
        )
        return 0.0

    # Measure direct overlap: how many meal name words appear in alt text
    query_overlap = query_words & alt_words
    overlap_ratio = len(query_overlap) / len(query_words)

    if overlap_ratio >= 0.8:
        # Almost all meal name words found in image description
        score = 0.9 + (overlap_ratio - 0.8) * 0.5  # 0.9–1.0
    elif overlap_ratio >= 0.5:
        # Majority of meal name words found
        score = 0.7 + (overlap_ratio - 0.5) * 0.67  # 0.7–0.9
    elif overlap_ratio > 0:
        # Some meal name words found
        score = 0.5 + overlap_ratio * 0.4  # 0.5–0.7
    else:
        # No direct overlap — check for generic food signals
        food_overlap = alt_words & _FOOD_SIGNALS
        if food_overlap:
            # It's a food photo, just not specifically this meal
            score = 0.4 + min(len(food_overlap), 3) * 0.03  # 0.43–0.49
        else:
            score = 0.1

    logger.debug(
        f"Image score={score:.2f}: query='{query}' | "
        f"overlap={query_overlap} ({overlap_ratio:.0%}) | alt='{alt[:80]}'"
    )
    return min(score, 1.0)


def _simplify_food_query(query: str) -> str:
    """Extract core food words from a meal name for simpler search.

    E.g. 'Honey Garlic Glazed Chicken Breast' → 'honey garlic chicken'
    """
    words = extract_words(query)
    food_words = words & _FOOD_SIGNALS
    remaining = words - _STOP_WORDS - _FOOD_SIGNALS
    # Keep food signals + up to 2 descriptive words
    result_words = food_words | set(list(remaining)[:2])
    return " ".join(sorted(result_words)) if result_words else query.lower()


extract_words = extract_words
