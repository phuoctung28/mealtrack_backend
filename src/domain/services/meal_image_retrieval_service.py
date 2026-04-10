"""
Meal image retrieval service — 3-source cascade.

Tries sources in order: SerpAPI → Unsplash → Gemini image generation.
Each source has an individual timeout. If one fails or returns None the
next source is tried. Returns (image_url, source_name) or (None, None)
if all sources are unavailable.
"""
import asyncio
import logging
from typing import Optional, Tuple

from src.domain.ports.meal_image_retrieval_port import MealImageRetrievalPort

logger = logging.getLogger(__name__)

# Per-source timeout in seconds
_SOURCE_TIMEOUT = 5.0


class MealImageRetrievalService:
    """Orchestrates image retrieval across multiple sources with fallback."""

    def __init__(
        self,
        serpapi_adapter: Optional[MealImageRetrievalPort],
        unsplash_adapter: Optional[MealImageRetrievalPort],
        gemini_adapter: Optional[MealImageRetrievalPort],
    ):
        self._sources = [
            ("serpapi", serpapi_adapter),
            ("unsplash", unsplash_adapter),
            ("gemini", gemini_adapter),
        ]

    async def retrieve(self, meal_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try each source in order and return on the first success.

        Returns:
            (image_url, source_name) or (None, None) if all fail.
        """
        for source_name, adapter in self._sources:
            if adapter is None:
                logger.debug("Image source '%s' not configured — skipping.", source_name)
                continue

            try:
                url = await asyncio.wait_for(
                    adapter.fetch_image(meal_name),
                    timeout=_SOURCE_TIMEOUT,
                )
                if url:
                    logger.info("Image retrieved from source='%s' for meal='%s'.", source_name, meal_name)
                    return url, source_name
                logger.debug("Source '%s' returned no image for '%s'.", source_name, meal_name)
            except asyncio.TimeoutError:
                logger.warning("Source '%s' timed out after %.1fs for '%s'.", source_name, _SOURCE_TIMEOUT, meal_name)
            except Exception as exc:
                logger.warning("Source '%s' failed for '%s': %s", source_name, meal_name, exc)

        logger.info("All image sources exhausted for '%s' — returning None.", meal_name)
        return None, None
