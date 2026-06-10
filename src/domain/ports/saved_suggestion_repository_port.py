"""Port interface for saved suggestion persistence operations."""

from abc import ABC, abstractmethod
from typing import Any


class SavedSuggestionRepositoryPort(ABC):
    """Abstract repository for saved meal suggestions."""

    @abstractmethod
    async def find_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all saved suggestions for a user, newest first.

        Returns list of dicts with keys: id, suggestion_id, meal_type,
        portion_multiplier, suggestion_data, saved_at.
        """
        pass

    @abstractmethod
    async def find_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> dict[str, Any] | None:
        """Find a specific saved suggestion by user + suggestion ID."""
        pass

    @abstractmethod
    async def save(
        self,
        user_id: str,
        suggestion_id: str,
        meal_type: str,
        portion_multiplier: float,
        suggestion_data: dict,
    ) -> dict[str, Any]:
        """Save a new suggestion. Returns the saved record as a dict."""
        pass

    @abstractmethod
    async def delete_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> bool:
        """Delete a saved suggestion. Returns True if deleted."""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count saved suggestions for a user."""
        pass
