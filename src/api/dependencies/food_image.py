"""Singleton factory for FoodImageSearchService (API layer)."""

from typing import Optional

from src.domain.services.meal_discovery.food_image_search_service import (
    FoodImageSearchService,
)

_instance: Optional[FoodImageSearchService] = None


def get_food_image_service() -> FoodImageSearchService:
    """Return singleton FoodImageSearchService with Pexels → Unsplash chain.

    When BRAVE_SEARCH_API_KEY is configured, enables web search
    cross-validation to reject images that don't match the meal name.
    """
    global _instance
    if _instance is None:
        from src.infra.adapters.pexels_image_adapter import PexelsImageAdapter
        from src.infra.adapters.unsplash_image_adapter import UnsplashImageAdapter
        from src.infra.config.settings import settings

        web_validator = None
        if settings.BRAVE_SEARCH_API_KEY:
            from src.infra.adapters.web_search_image_validator import (
                WebSearchImageValidator,
            )

            web_validator = WebSearchImageValidator(settings.BRAVE_SEARCH_API_KEY)

        _instance = FoodImageSearchService(
            adapters=[PexelsImageAdapter(), UnsplashImageAdapter()],
            web_validator=web_validator,
        )
    return _instance
