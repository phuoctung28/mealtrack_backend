"""
Unsplash image adapter — fetches a food photo from Unsplash.

Docs: https://unsplash.com/documentation#search-photos
Free tier: 50 requests / hour (Demo), production requires approval.
"""
import logging
from typing import Optional

import httpx

from src.domain.ports.meal_image_retrieval_port import MealImageRetrievalPort

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.unsplash.com/search/photos"


class UnsplashImageAdapter(MealImageRetrievalPort):
    """Retrieve a meal image URL using the Unsplash Photos search API."""

    def __init__(self, access_key: str):
        self._access_key = access_key

    async def fetch_image(self, meal_name: str) -> Optional[str]:
        """Search Unsplash for the meal and return the first result's regular URL."""
        query = f"{meal_name} food"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    _SEARCH_URL,
                    params={
                        "query": query,
                        "per_page": 1,
                        "orientation": "squarish",
                    },
                    headers={"Authorization": f"Client-ID {self._access_key}"},
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            if not results:
                logger.debug("Unsplash returned no results for '%s'.", meal_name)
                return None

            url = results[0].get("urls", {}).get("regular")
            if url:
                logger.debug("Unsplash image found for '%s': %s", meal_name, url[:80])
            return url

        except Exception as exc:
            logger.warning("Unsplash image fetch failed for '%s': %s", meal_name, exc)
            return None


def get_unsplash_image_adapter() -> Optional[UnsplashImageAdapter]:
    """Return adapter if UNSPLASH_ACCESS_KEY is configured, else None."""
    from src.infra.config.settings import settings
    if not settings.UNSPLASH_ACCESS_KEY:
        return None
    return UnsplashImageAdapter(settings.UNSPLASH_ACCESS_KEY)
