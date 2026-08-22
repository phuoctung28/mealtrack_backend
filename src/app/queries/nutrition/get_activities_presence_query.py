"""
Activities presence query for fetching meal existence per date.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetActivitiesPresenceQuery(Query):
    """Query to get boolean presence map for dates with meals."""
    user_id: str
    start_date: date
    end_date: date
    header_timezone: Optional[str] = None
