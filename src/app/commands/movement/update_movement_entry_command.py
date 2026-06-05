"""Command to update an existing movement entry."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class UpdateMovementEntryCommand(Command):
    user_id: str
    entry_id: str
    duration_min: int
    kcal_burned: float
    intensity: str
    include_in_balance: bool
