"""
Query for getting meals by specific date.
"""
from dataclasses import dataclass
from datetime import date

from src.app.events.base import Query


@dataclass
class GetMealsByDateQuery(Query):
    """Query for getting meals for a specific date."""
    user_id: str
    meal_date: date
