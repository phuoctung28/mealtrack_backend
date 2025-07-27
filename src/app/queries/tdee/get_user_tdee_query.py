"""
Query to get user's TDEE calculation data.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetUserTdeeQuery(Query):
    """Query to get user's current TDEE calculation."""
    user_id: str