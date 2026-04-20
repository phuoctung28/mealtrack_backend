"""
Pexels image search adapter for food photos (NM-72).
Uses Pexels API v1 — returns landscape photos ≥400px wide.
"""
import logging
from typing import Optional

import httpx

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com/v1/search"
MIN_WIDTH = 400


class PexelsImageAdapter(FoodImageSearchPort):
    """Searches Pexels for food photos. Returns None if key missing or request fails."""

    async def search(self, query: str) -> Optional[FoodImageResult]:
        api_key = settings.PEXELS_API_KEY
        if not api_key:
            logger.debug("PEXELS_API_KEY not configured, skipping Pexels search")
            return None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    PEXELS_API_URL,
                    headers={"Authorization": api_key},
                    params={"query": query, "per_page": 3, "orientation": "landscape"},
                )
                response.raise_for_status()
                data = response.json()

            photos = data.get("photos", [])
            for photo in photos:
                src = photo.get("src", {})
                url = src.get("large", "") or src.get("medium", "")
                thumbnail = src.get("medium", "") or src.get("small", "")
                alt = photo.get("alt", "")
                width = photo.get("width", 0)

                # Validate: must have alt text and meet minimum width
                if not url or not alt or width < MIN_WIDTH:
                    continue

                return FoodImageResult(
                    url=url,
                    thumbnail_url=thumbnail or url,
                    source="pexels",
                    photographer=photo.get("photographer"),
                    photographer_url=photo.get("photographer_url"),
                    alt_text=alt,
                )

        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {e}")

        return None
