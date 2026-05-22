"""Command to log a hydration (non-caloric) drink entry."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class LogHydrationCommand(Command):
    user_id: str
    drink_id: str  # must be a "hydration" category drink
    volume_ml: int
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
