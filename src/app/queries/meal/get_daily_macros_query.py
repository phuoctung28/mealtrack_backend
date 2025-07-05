"""
Get daily macros query.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyMacrosQuery(Query):
    """Query to get daily macros summary."""
    target_date: Optional[date] = None