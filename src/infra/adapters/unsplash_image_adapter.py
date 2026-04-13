"""
Unsplash image search adapter for food photos (NM-72).
Uses Unsplash API v1 — fallback when Pexels returns nothing.

Compliance: https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines
- Hotlink photos via photo.urls (never re-host)
- Trigger download_location when user "saves" a photo
- Attribute: "Photo by {name} on Unsplash" with linked profile + UTM
"""
import logging
from typing import Optional

import httpx

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)

UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
UTM_PARAMS = "utm_source=nutree&utm_medium=referral"


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
                username = user.get("username", "")
                profile_url = f"https://unsplash.com/@{username}?{UTM_PARAMS}" if username else None

                # Required by Unsplash API guidelines — trigger when user saves/logs
                download_location = photo.get("links", {}).get("download_location")

                return FoodImageResult(
                    url=url,
                    thumbnail_url=thumbnail or url,
                    source="unsplash",
                    photographer=photographer,
                    photographer_url=profile_url,
                    download_location=download_location,
                    alt_text=photo.get("alt_description") or photo.get("description") or "",
                )

        except Exception as e:
            logger.warning(f"Unsplash search failed for '{query}': {e}")

        return None

    @staticmethod
    async def trigger_download(download_location: str) -> None:
        """Fire Unsplash download event (required by API guidelines)."""
        access_key = settings.UNSPLASH_ACCESS_KEY
        if not access_key or not download_location:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get(
                    download_location,
                    headers={"Authorization": f"Client-ID {access_key}"},
                )
        except Exception as e:
            logger.warning(f"Unsplash download trigger failed: {e}")
