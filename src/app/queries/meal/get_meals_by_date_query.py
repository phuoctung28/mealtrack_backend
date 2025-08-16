"""
Get meals by date query.
"""
from dataclasses import dataclass
from datetime import date

from src.app.events.base import Query


@dataclass
class GetMealsByDateQuery(Query):
    """Query to get meals for a specific date."""
    user_id: str
    target_date: date