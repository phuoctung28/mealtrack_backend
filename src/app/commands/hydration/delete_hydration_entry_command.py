"""Command to soft-delete a hydration log entry."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteHydrationEntryCommand(Command):
    user_id: str
    entry_id: str
