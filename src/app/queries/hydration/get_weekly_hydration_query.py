"""Query for weekly hydration chart data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetWeeklyHydrationQuery(Query):
    user_id: str
    start_date: Optional[date] = field(default=None)
    header_timezone: Optional[str] = field(default=None)
