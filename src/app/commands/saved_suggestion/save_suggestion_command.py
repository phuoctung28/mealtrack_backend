"""Command to save a meal suggestion to user's bookmarks."""

from dataclasses import dataclass, field
from typing import Any, Dict

from src.app.events.base import Command


@dataclass
class SaveSuggestionCommand(Command):
    """Save a meal suggestion for a user."""

    user_id: str
    suggestion_id: str
    meal_type: str
    portion_multiplier: int = 1
    suggestion_data: Dict[str, Any] = field(default_factory=dict)
