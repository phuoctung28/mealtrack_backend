"""
Get meal planning summary query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealPlanningSummaryQuery(Query):
    """Query to get meal planning summary for a profile."""
    user_profile_id: str