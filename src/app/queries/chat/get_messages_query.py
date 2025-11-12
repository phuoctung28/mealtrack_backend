"""
Query to get messages from a thread.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMessagesQuery(Query):
    """Query to get messages from a thread."""
    thread_id: str
    user_id: str  # For authorization
    limit: int = 100
    offset: int = 0

