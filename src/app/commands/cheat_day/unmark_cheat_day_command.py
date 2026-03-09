"""Command to unmark a cheat day."""
from dataclasses import dataclass
from datetime import date


@dataclass
class UnmarkCheatDayCommand:
    user_id: str
    date: date
