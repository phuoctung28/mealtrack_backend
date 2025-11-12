"""
Query to get a single thread by ID.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetThreadQuery(Query):
    """Query to get a single thread with messages."""
    thread_id: str
    user_id: str  # For authorization

