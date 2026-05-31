"""Command to log a movement entry."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class LogMovementCommand(Command):
    user_id: str
    activity_name: str
    duration_min: int
    kcal_burned: float
    intensity: str
    include_in_balance: bool
    activity_id: Optional[str] = None
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
