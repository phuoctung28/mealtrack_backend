"""
Get daily activities query.
"""
from dataclasses import dataclass
from datetime import datetime

from src.app.events.base import Query


@dataclass
class GetDailyActivitiesQuery(Query):
    """Query to get all activities for a specific date."""
    target_date: datetime