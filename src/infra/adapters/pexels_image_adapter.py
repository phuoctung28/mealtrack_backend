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
        results = await self.search_multiple(query, count=1)
        return results[0] if results else None

    async def search_multiple(
        self, query: str, count: int = 5
    ) -> list[FoodImageResult]:
        """Return up to `count` candidates for SigLIP scoring.

        Prefixes the query with "food" so Pexels biases toward food photography.
        """
        api_key = settings.PEXELS_API_KEY
        if not api_key:
            logger.debug("PEXELS_API_KEY not configured, skipping Pexels search")
            return []

        # Prefix with "food" so Pexels biases results toward food photography.
        food_query = f"food {query}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    PEXELS_API_URL,
                    headers={"Authorization": api_key},
                    params={
                        "query": food_query,
                        "per_page": count,
                        "orientation": "landscape",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for photo in data.get("photos", []):
                src = photo.get("src", {})
                url = src.get("large", "") or src.get("medium", "")
                thumbnail = src.get("medium", "") or src.get("small", "")
                alt = photo.get("alt", "")
                width = photo.get("width", 0)

                if not url or not alt or width < MIN_WIDTH:
                    continue

                results.append(
                    FoodImageResult(
                        url=url,
                        thumbnail_url=thumbnail or url,
                        source="pexels",
                        photographer=photo.get("photographer"),
                        photographer_url=photo.get("photographer_url"),
                        alt_text=alt,
                    )
                )

            return results

        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {e}")
            return []
