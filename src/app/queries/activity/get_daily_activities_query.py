"""
Get daily activities query.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyActivitiesQuery(Query):
    """Query to get all activities for a specific date and user."""
    user_id: str
    target_date: datetime
    language: Optional[str] = field(default="en")