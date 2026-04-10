"""Port interface for meal image retrieval adapters."""
from abc import ABC, abstractmethod
from typing import Optional


class MealImageRetrievalPort(ABC):
    """Interface that each image source adapter must implement."""

    @abstractmethod
    async def fetch_image(self, meal_name: str) -> Optional[str]:
        """
        Attempt to retrieve or generate an image URL for the given meal name.

        Args:
            meal_name: Human-readable meal name, e.g. "Grilled Chicken with Rice"

        Returns:
            A publicly accessible image URL, or None if retrieval failed.
        """
