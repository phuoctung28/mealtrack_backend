"""
Thread domain model for chat conversations.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.domain.services.timezone_utils import utc_now, format_iso_utc
from .chat_enums import ThreadStatus
from .message import Message


@dataclass
class Thread:
    """
    Aggregate root representing a conversation thread.
    A thread contains multiple messages between user and assistant.
    """
    thread_id: str  # UUID as string
    user_id: str  # UUID as string
    title: Optional[str]
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    messages: List[Message] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.thread_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for thread_id: {self.thread_id}")
        
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        # Validate title
        if self.title and len(self.title) > 255:
            raise ValueError(f"Title too long (max 255 chars): {len(self.title)}")
        
        # Validate status
        if not isinstance(self.status, ThreadStatus):
            raise ValueError(f"Invalid thread status: {self.status}")
    
    @classmethod
    def create_new(
        cls,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Thread':
        """Factory method to create a new thread."""
        now = utc_now()
        return cls(
            thread_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title or "New Conversation",
            status=ThreadStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            messages=[]
        )

    def add_message(self, message: Message) -> 'Thread':
        """Add a message to the thread and return updated thread."""
        if message.thread_id != self.thread_id:
            raise ValueError(f"Message thread_id {message.thread_id} does not match thread {self.thread_id}")

        # Create new thread with updated messages
        updated_messages = self.messages + [message]

        return Thread(
            thread_id=self.thread_id,
            user_id=self.user_id,
            title=self.title,
            status=self.status,
            created_at=self.created_at,
            updated_at=utc_now(),
            metadata=self.metadata,
            messages=updated_messages
        )

    def archive(self) -> 'Thread':
        """Archive the thread."""
        return Thread(
            thread_id=self.thread_id,
            user_id=self.user_id,
            title=self.title,
            status=ThreadStatus.ARCHIVED,
            created_at=self.created_at,
            updated_at=utc_now(),
            metadata=self.metadata,
            messages=self.messages
        )

    def delete(self) -> 'Thread':
        """Soft delete the thread."""
        return Thread(
            thread_id=self.thread_id,
            user_id=self.user_id,
            title=self.title,
            status=ThreadStatus.DELETED,
            created_at=self.created_at,
            updated_at=utc_now(),
            metadata=self.metadata,
            messages=self.messages
        )

    def update_title(self, title: str) -> 'Thread':
        """Update thread title."""
        if len(title) > 255:
            raise ValueError(f"Title too long (max 255 chars): {len(title)}")

        return Thread(
            thread_id=self.thread_id,
            user_id=self.user_id,
            title=title,
            status=self.status,
            created_at=self.created_at,
            updated_at=utc_now(),
            metadata=self.metadata,
            messages=self.messages
        )
    
    def get_message_count(self) -> int:
        """Get the number of messages in this thread."""
        # Check for cached message count (set by repository to avoid N+1 queries)
        if hasattr(self, '_cached_message_count'):
            return self._cached_message_count
        return len(self.messages)
    
    def get_last_message(self) -> Optional[Message]:
        """Get the most recent message in the thread."""
        return self.messages[-1] if self.messages else None
    
    def to_dict(self, include_messages: bool = False) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "title": self.title,
            "status": str(self.status),
            "created_at": format_iso_utc(self.created_at),
            "updated_at": format_iso_utc(self.updated_at),
            "metadata": self.metadata or {},
            "message_count": self.get_message_count()
        }

        last_message = self.get_last_message()
        if last_message:
            result["last_message_at"] = format_iso_utc(last_message.created_at)

        if include_messages:
            result["messages"] = [msg.to_dict() for msg in self.messages]

        return result

