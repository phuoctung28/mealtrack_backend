"""Reject suggestion command."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RejectSuggestionCommand:
    """Command to reject suggestion with optional feedback."""

    user_id: str
    suggestion_id: str
    feedback: Optional[str]
