"""Port for validating whether a URL hosts a usable food image."""
from abc import ABC, abstractmethod


class WebSearchValidatorPort(ABC):
    """Checks whether a search-result image URL is accessible and valid."""

    @abstractmethod
    async def is_valid_image_url(self, url: str) -> bool:
        """Return True if the URL serves a valid, accessible image."""
