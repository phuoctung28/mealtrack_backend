"""
SerpAPI image adapter — fetches a food image from Google Images via SerpAPI.

Docs: https://serpapi.com/images-results
Free tier: 100 searches / month.
"""
import logging
from typing import Optional

import httpx

from src.domain.ports.meal_image_retrieval_port import MealImageRetrievalPort

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://serpapi.com/search"


class SerpApiImageAdapter(MealImageRetrievalPort):
    """Retrieve a meal image URL using SerpAPI Google Images search."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_image(self, meal_name: str) -> Optional[str]:
        """Search Google Images for the meal and return the first usable URL."""
        query = f"{meal_name} food dish"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    _SEARCH_URL,
                    params={
                        "engine": "google_images",
                        "q": query,
                        "num": 5,
                        "api_key": self._api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()

            images = data.get("images_results", [])
            for img in images:
                url = img.get("original") or img.get("thumbnail")
                if url and self._is_usable(url):
                    logger.debug("SerpAPI image found for '%s': %s", meal_name, url[:80])
                    return url

            logger.debug("SerpAPI returned no usable images for '%s'.", meal_name)
            return None

        except Exception as exc:
            logger.warning("SerpAPI image fetch failed for '%s': %s", meal_name, exc)
            return None

    @staticmethod
    def _is_usable(url: str) -> bool:
        """Reject SVGs and data URIs."""
        lower = url.lower()
        return not lower.startswith("data:") and not lower.endswith(".svg")


def get_serpapi_image_adapter() -> Optional[SerpApiImageAdapter]:
    """Return adapter if SERPAPI_KEY is configured, else None."""
    from src.infra.config.settings import settings
    if not settings.SERPAPI_KEY:
        return None
    return SerpApiImageAdapter(settings.SERPAPI_KEY)
