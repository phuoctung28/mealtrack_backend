"""Fake meal suggestion repository for testing."""
from datetime import datetime
from typing import List, Optional

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_suggestion_repository_port import MealSuggestionRepositoryPort


class FakeMealSuggestionRepository(MealSuggestionRepositoryPort):
    """In-memory implementation of MealSuggestionRepositoryPort for testing."""
    
    def __init__(self):
        self._suggestions: dict[str, MealSuggestion] = {}
        self._sessions: dict[str, SuggestionSession] = {}
    
    async def save_session(self, session: SuggestionSession) -> None:
        """Save suggestion session with 4-hour TTL."""
        self._sessions[session.id] = session
    
    async def get_session(self, session_id: str) -> Optional[SuggestionSession]:
        """Retrieve session by ID."""
        return self._sessions.get(session_id)
    
    async def update_session(self, session: SuggestionSession) -> None:
        """Update existing session (maintains remaining TTL)."""
        if session.id in self._sessions:
            self._sessions[session.id] = session
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session and all associated suggestions."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            # Also delete associated suggestions
            suggestion_ids = [
                sug_id for sug_id, sug in self._suggestions.items()
                if sug.session_id == session_id
            ]
            for sug_id in suggestion_ids:
                del self._suggestions[sug_id]
    
    async def save_suggestions(self, suggestions: List[MealSuggestion]) -> None:
        """Save batch of suggestions with 4-hour TTL."""
        for suggestion in suggestions:
            self._suggestions[suggestion.id] = suggestion
    
    async def get_suggestion(self, suggestion_id: str) -> Optional[MealSuggestion]:
        """Retrieve single suggestion by ID."""
        return self._suggestions.get(suggestion_id)
    
    async def update_suggestion(self, suggestion: MealSuggestion) -> None:
        """Update suggestion (e.g., status change)."""
        if suggestion.id in self._suggestions:
            self._suggestions[suggestion.id] = suggestion
