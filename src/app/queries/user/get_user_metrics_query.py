"""
Query to get user's current metrics for settings display.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetUserMetricsQuery(Query):
    """Query to get user's current metrics."""
    user_id: str

