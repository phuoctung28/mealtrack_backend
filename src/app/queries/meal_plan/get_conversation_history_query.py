"""
Get conversation history query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetConversationHistoryQuery(Query):
    """Query to get conversation history."""
    conversation_id: str