"""
Domain events for chat feature.
"""
from dataclasses import dataclass
from typing import Dict, Any

from src.app.events.base import DomainEvent


@dataclass
class MessageSentEvent(DomainEvent):
    """Event fired when a message is sent."""
    thread_id: str
    message_id: str
    user_id: str
    role: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class ThreadCreatedEvent(DomainEvent):
    """Event fired when a thread is created."""
    thread_id: str
    user_id: str
    title: str


@dataclass
class ThreadDeletedEvent(DomainEvent):
    """Event fired when a thread is deleted."""
    thread_id: str
    user_id: str

