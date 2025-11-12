"""
Query to get list of threads for a user.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetThreadsQuery(Query):
    """Query to get threads for a user."""
    user_id: str
    limit: int = 50
    offset: int = 0
    include_deleted: bool = False

