"""Singleton factory for FoodImageSearchService (API layer)."""
from typing import Optional

from src.domain.services.meal_discovery.food_image_search_service import FoodImageSearchService

_instance: Optional[FoodImageSearchService] = None


def get_food_image_service() -> FoodImageSearchService:
    """Return singleton FoodImageSearchService with Pexels → Unsplash chain."""
    global _instance
    if _instance is None:
        from src.infra.adapters.pexels_image_adapter import PexelsImageAdapter
        from src.infra.adapters.unsplash_image_adapter import UnsplashImageAdapter

        _instance = FoodImageSearchService(
            adapters=[PexelsImageAdapter(), UnsplashImageAdapter()]
        )
    return _instance
