"""
Unsplash image search adapter for food photos (NM-72).
Uses Unsplash API v1 — fallback when Pexels returns nothing.
"""
import logging
from typing import Optional

import httpx

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)

UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"


class UnsplashImageAdapter(FoodImageSearchPort):
    """Searches Unsplash for food photos. Returns None if key missing or request fails."""

    async def search(self, query: str) -> Optional[FoodImageResult]:
        access_key = settings.UNSPLASH_ACCESS_KEY
        if not access_key:
            logger.debug("UNSPLASH_ACCESS_KEY not configured, skipping Unsplash search")
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    UNSPLASH_API_URL,
                    headers={"Authorization": f"Client-ID {access_key}"},
                    params={"query": query, "per_page": 3, "orientation": "landscape"},
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            for photo in results:
                urls = photo.get("urls", {})
                url = urls.get("regular", "")
                thumbnail = urls.get("small", "")
                if not url:
                    continue

                user = photo.get("user", {})
                photographer = user.get("name")

                return FoodImageResult(
                    url=url,
                    thumbnail_url=thumbnail or url,
                    source="unsplash",
                    photographer=photographer,
                )

        except Exception as e:
            logger.warning(f"Unsplash search failed for '{query}': {e}")

        return None
