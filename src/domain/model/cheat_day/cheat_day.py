"""Cheat day domain entity."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class CheatDay:
    """A day manually marked as cheat day by user. Auto-detection is computed, not stored."""

    cheat_day_id: str
    user_id: str
    date: date
    marked_at: datetime
