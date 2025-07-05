"""
Get user profile query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetUserProfileQuery(Query):
    """Query to get user profile."""
    user_id: str