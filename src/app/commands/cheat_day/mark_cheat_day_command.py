"""Command to mark a date as cheat day."""

from dataclasses import dataclass
from datetime import date


@dataclass
class MarkCheatDayCommand:
    user_id: str
    date: date
