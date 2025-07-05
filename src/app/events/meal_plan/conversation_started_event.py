"""
Conversation started event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class ConversationStartedEvent(DomainEvent):
    """Event raised when conversation starts."""
    aggregate_id: str
    conversation_id: str
    user_id: str
    initial_state: str
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))