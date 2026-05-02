"""Command to delete a saved suggestion."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteSavedSuggestionCommand(Command):
    """Remove a saved suggestion by suggestion_id for a user."""

    user_id: str
    suggestion_id: str
