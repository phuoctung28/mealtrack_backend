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
from src.domain.ports.web_search_validator_port import WebSearchValidatorPort
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
    "risotto", "biryani", "paella", "gnocchi", "lasagna",
    "kebab", "satay", "tempeh", "miso", "teriyaki",
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
        web_validator: Optional[WebSearchValidatorPort] = None,
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

    Strategy: prioritize core food word matches over full-name overlap.
    Pexels/Unsplash alt text is short ("salmon on plate") while meal names
    are long ("Honey Garlic Glazed Salmon"). Matching the core food word
    ("salmon") is a strong signal — modifiers are cooking style, not visual.

    Scoring:
    - 0.0: Non-food image (buildings, cars, etc.)
    - 0.3: No alt text — moderate trust in search API
    - 0.5: Generic food photo (food signals but no query match)
    - 0.85: Core food word from meal name found in alt text
    - 0.9+: Multiple query words match (strong match)
    """
    alt = result.alt_text or ""
    if not alt:
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

    query_overlap = query_words & alt_words

    # Core food word match: the primary ingredient/dish type from meal name
    # e.g. "salmon" in "Honey Garlic Glazed Salmon"
    core_food_words = query_words & _FOOD_SIGNALS
    core_match = bool(core_food_words & alt_words)

    if not query_overlap:
        # No direct overlap — check for generic food signals in alt text
        food_overlap = alt_words & _FOOD_SIGNALS
        if food_overlap:
            score = 0.5
        else:
            score = 0.1
    elif core_match:
        # Core food word found — strong signal regardless of modifier overlap
        # Bonus for additional word matches
        extra = len(query_overlap) - 1  # beyond the first match
        score = 0.85 + min(extra, 3) * 0.05  # 0.85–1.0
    else:
        # Non-core words match (modifiers like "grilled", "honey")
        score = 0.6 + min(len(query_overlap), 3) * 0.08  # 0.68–0.84

    logger.debug(
        f"Image score={score:.2f}: query='{query}' | "
        f"overlap={query_overlap} | core_match={core_match} | alt='{alt[:80]}'"
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
