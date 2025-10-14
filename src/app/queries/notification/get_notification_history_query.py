"""
Query to get user notification history.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GetNotificationHistoryQuery:
    """Query to get notification history"""
    user_id: str
    notification_type: Optional[str] = None
    limit: int = 50
    offset: int = 0

