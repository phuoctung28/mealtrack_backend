"""Repository port for meal suggestion domain."""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession


class MealSuggestionRepositoryPort(ABC):
    """Port for meal suggestion data access."""

    @abstractmethod
    async def save_session(self, session: SuggestionSession) -> None:
        """Save suggestion session with 4-hour TTL."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SuggestionSession]:
        """Retrieve session by ID."""
        pass

    @abstractmethod
    async def update_session(self, session: SuggestionSession) -> None:
        """Update existing session (maintains remaining TTL)."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session and all associated suggestions."""
        pass

    @abstractmethod
    async def save_suggestions(self, suggestions: List[MealSuggestion]) -> None:
        """Save batch of suggestions with 4-hour TTL."""
        pass

    @abstractmethod
    async def get_suggestion(self, suggestion_id: str) -> Optional[MealSuggestion]:
        """Retrieve single suggestion by ID."""
        pass

    @abstractmethod
    async def update_suggestion(self, suggestion: MealSuggestion) -> None:
        """Update suggestion (e.g., status change)."""
        pass

