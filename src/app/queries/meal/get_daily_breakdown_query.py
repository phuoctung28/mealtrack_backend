"""
Get daily breakdown query.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyBreakdownQuery(Query):
    """Query to get 7-day macro breakdown (actual vs target per day)."""

    user_id: str
    week_start: Optional[date] = None
    header_timezone: Optional[str] = None
