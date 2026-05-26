"""Command to log a caloric drink entry (creates both a meal and a hydration entry)."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class LogCaloricDrinkCommand(Command):
    user_id: str
    drink_id: str  # must be a "caloric" category drink
    volume_ml: int
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
    language: str = "en"
