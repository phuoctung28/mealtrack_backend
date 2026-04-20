"""Abstract port for food image search providers (Pexels, Unsplash, etc.)."""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.model.meal_discovery.food_image import FoodImageResult


class FoodImageSearchPort(ABC):
    """Interface for external image search adapters."""

    @abstractmethod
    async def search(self, query: str) -> Optional[FoodImageResult]:
        """
        Search for a food photo matching the query.

        Args:
            query: English food description (2-4 words)

        Returns:
            FoodImageResult if a suitable image is found, None otherwise.
            Must never raise — return None on any error.
        """
