"""Command to delete a movement entry."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteMovementEntryCommand(Command):
    user_id: str
    entry_id: str
