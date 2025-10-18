"""
Query to get notification preferences for a user.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetNotificationPreferencesQuery(Query):
    """Query to get notification preferences for a user."""
    user_id: str
