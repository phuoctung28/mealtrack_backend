"""Get session suggestions query."""
from dataclasses import dataclass


@dataclass
class GetSessionSuggestionsQuery:
    """Query to get current session's suggestions."""

    user_id: str
    session_id: str
