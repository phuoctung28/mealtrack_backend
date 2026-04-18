"""Port for validating whether a URL hosts a usable food image."""
from abc import ABC, abstractmethod

from src.domain.model.meal_discovery.food_image import FoodImageResult


class WebSearchValidatorPort(ABC):
    """Checks whether a search-result image URL is accessible and valid."""

    @abstractmethod
    async def is_valid_image_url(self, url: str) -> bool:
        """Return True if the URL serves a valid, accessible image."""

    @abstractmethod
    async def score(self, meal_name: str, image: FoodImageResult) -> float:
        """Score how relevant/valid an image is for the given meal name.

        Returns a float in 0.0–1.0 where higher means a better match.
        Implementations should return 0.5 (neutral) on any error.
        """
