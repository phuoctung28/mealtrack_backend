"""Get bulk activities query."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetBulkActivitiesQuery(Query):
    """Query to get all activities for a date range, grouped by date."""

    user_id: str
    start_date: date
    end_date: date
    language: Optional[str] = field(default="en")
    header_timezone: Optional[str] = field(default=None)
