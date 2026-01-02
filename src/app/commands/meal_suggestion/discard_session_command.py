"""Discard session command."""
from dataclasses import dataclass


@dataclass
class DiscardSessionCommand:
    """Command to discard entire suggestion session."""

    user_id: str
    session_id: str
