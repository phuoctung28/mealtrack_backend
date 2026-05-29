"""Get daily hydration query."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyHydrationQuery(Query):
    """Query to get daily hydration summary and log entries."""

    user_id: str
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
    language: str = "en"
