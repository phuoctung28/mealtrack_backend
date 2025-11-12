"""
Command to delete a chat thread.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteThreadCommand(Command):
    """Command to delete a chat thread (soft delete)."""
    thread_id: str
    user_id: str  # For authorization

