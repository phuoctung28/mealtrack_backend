"""
Web search cross-validation for food images.
Searches Brave for the meal name and scores how well the stock photo
alt text matches web descriptions of that meal.
Gracefully degrades: returns 0.5 (neutral) on any error.
"""
import logging
from typing import Optional, Set

import httpx

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.services.meal_discovery import extract_words

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_SEARCH_TIMEOUT = 3.0  # seconds — fast timeout to avoid blocking image pipeline


class WebSearchImageValidator:
    """
    Scores food images against web search results for the meal name.

    How it works:
    1. Search Brave for "[meal name] dish recipe"
    2. Extract descriptive keywords from result titles + snippets
    3. Score overlap between web keywords and the image's alt text
    4. Higher overlap = higher confidence the image depicts the meal

    Cached per meal name to avoid repeated API calls for same dish.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._keyword_cache: dict[str, Set[str]] = {}

    async def score(
        self, meal_name: str, image: FoodImageResult
    ) -> float:
        """Return 0.0–1.0 score of how well image matches the meal per web search.

        Scoring:
        - 0.5: No alt text or web search failed (neutral — don't penalize)
        - 0.0–0.3: Zero overlap between web keywords and alt text
        - 0.5–0.7: Some overlap (image partially matches)
        - 0.8–1.0: Strong overlap (image likely depicts this specific meal)
        """
        try:
            alt_text = image.alt_text or ""
            if not alt_text:
                return 0.5  # No alt text — neutral

            web_keywords = await self._get_meal_keywords(meal_name)
            if not web_keywords:
                return 0.5  # Web search unavailable — neutral

            alt_words = extract_words(alt_text)
            overlap = alt_words & web_keywords

            if not overlap:
                return 0.2  # No overlap — image likely unrelated

            # Score based on how many web keywords appear in alt text
            overlap_ratio = len(overlap) / min(len(web_keywords), 10)
            score = 0.5 + min(overlap_ratio, 1.0) * 0.5  # 0.5–1.0

            logger.debug(
                f"Web score={score:.2f}: meal='{meal_name}' | "
                f"overlap={list(overlap)[:5]} ({len(overlap)}/{len(web_keywords)})"
            )
            return score
        except Exception as e:
            logger.warning(f"Web image scoring error for '{meal_name}': {e}")
            return 0.5  # Graceful degradation

    async def _get_meal_keywords(self, meal_name: str) -> Set[str]:
        """Fetch and cache descriptive keywords for a meal from web search."""
        key = meal_name.strip().lower()
        if key in self._keyword_cache:
            return self._keyword_cache[key]

        keywords = await self._search_meal_keywords(meal_name)
        self._keyword_cache[key] = keywords

        # Keep cache bounded
        if len(self._keyword_cache) > 2000:
            keys = list(self._keyword_cache.keys())
            for k in keys[:1000]:
                del self._keyword_cache[k]

        return keywords

    async def _search_meal_keywords(self, meal_name: str) -> Set[str]:
        """Search Brave for meal name and extract food-relevant keywords."""
        try:
            async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT) as client:
                response = await client.get(
                    BRAVE_SEARCH_URL,
                    params={"q": f"{meal_name} dish recipe food", "count": 5},
                    headers={
                        "X-Subscription-Token": self._api_key,
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("web", {}).get("results", [])
            if not results:
                return set()

            text_parts = []
            for r in results[:5]:
                text_parts.append(r.get("title", ""))
                text_parts.append(r.get("description", ""))

            combined = " ".join(text_parts)
            keywords = extract_words(combined)

            # Remove overly generic words
            generic = {
                "recipe", "recipes", "food", "dish", "best", "easy",
                "simple", "make", "how", "home", "cook", "cooking",
                "minute", "minutes", "time", "step", "steps",
                "the", "and", "with", "for", "this", "that",
                "from", "your", "you", "are", "will", "can",
            }
            keywords -= generic

            logger.debug(
                f"Web keywords for '{meal_name}': {list(keywords)[:15]}"
            )
            return keywords

        except Exception as e:
            logger.warning(f"Brave search for meal keywords failed: {e}")
            return set()
