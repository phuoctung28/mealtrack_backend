"""
Query to get user notification preferences.
"""
from dataclasses import dataclass


@dataclass
class GetNotificationPreferencesQuery:
    """Query to get notification preferences"""
    user_id: str

