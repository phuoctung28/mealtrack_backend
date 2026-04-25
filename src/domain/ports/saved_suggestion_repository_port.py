"""Port interface for saved suggestion persistence operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SavedSuggestionRepositoryPort(ABC):
    """Abstract repository for saved meal suggestions."""

    @abstractmethod
    def find_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all saved suggestions for a user, newest first.

        Returns list of dicts with keys: id, suggestion_id, meal_type,
        portion_multiplier, suggestion_data, saved_at.
        """
        pass

    @abstractmethod
    def find_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a specific saved suggestion by user + suggestion ID."""
        pass

    @abstractmethod
    def save(
        self,
        user_id: str,
        suggestion_id: str,
        meal_type: str,
        portion_multiplier: float,
        suggestion_data: dict,
    ) -> Dict[str, Any]:
        """Save a new suggestion. Returns the saved record as a dict."""
        pass

    @abstractmethod
    def delete_by_user_and_suggestion(self, user_id: str, suggestion_id: str) -> bool:
        """Delete a saved suggestion. Returns True if deleted."""
        pass

    @abstractmethod
    def count_by_user(self, user_id: str) -> int:
        """Count saved suggestions for a user."""
        pass
