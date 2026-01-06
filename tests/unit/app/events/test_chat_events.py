"""
Unit tests for chat events.
"""
import pytest
from datetime import datetime

from src.app.events.chat_events import (
    MessageSentEvent,
    ThreadCreatedEvent,
    ThreadDeletedEvent
)


@pytest.mark.unit
class TestChatEvents:
    """Test suite for chat domain events."""

    def test_message_sent_event(self):
        """Test MessageSentEvent creation."""
        event = MessageSentEvent(
            thread_id="thread_123",
            message_id="msg_456",
            user_id="user_789",
            role="user",
            content="Hello, world!",
            metadata={"timestamp": "2024-01-01T00:00:00Z"}
        )
        
        assert event.thread_id == "thread_123"
        assert event.message_id == "msg_456"
        assert event.user_id == "user_789"
        assert event.role == "user"
        assert event.content == "Hello, world!"
        assert event.metadata == {"timestamp": "2024-01-01T00:00:00Z"}
        assert isinstance(event.event_id, str)
        assert isinstance(event.occurred_at, datetime)

    def test_thread_created_event(self):
        """Test ThreadCreatedEvent creation."""
        event = ThreadCreatedEvent(
            thread_id="thread_123",
            user_id="user_789",
            title="New Conversation"
        )
        
        assert event.thread_id == "thread_123"
        assert event.user_id == "user_789"
        assert event.title == "New Conversation"
        assert isinstance(event.event_id, str)
        assert isinstance(event.occurred_at, datetime)

    def test_thread_deleted_event(self):
        """Test ThreadDeletedEvent creation."""
        event = ThreadDeletedEvent(
            thread_id="thread_123",
            user_id="user_789"
        )
        
        assert event.thread_id == "thread_123"
        assert event.user_id == "user_789"
        assert isinstance(event.event_id, str)
        assert isinstance(event.occurred_at, datetime)

