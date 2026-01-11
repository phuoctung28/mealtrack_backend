"""
Message domain model for chat conversations.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from src.domain.services.timezone_utils import utc_now, format_iso_utc
from .chat_enums import MessageRole


@dataclass
class Message:
    """
    Value object representing a single message in a conversation.
    Messages are immutable once created.
    """
    message_id: str  # UUID as string
    thread_id: str  # UUID as string
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.message_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for message_id: {self.message_id}")
        
        try:
            uuid.UUID(self.thread_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for thread_id: {self.thread_id}")
        
        # Validate content
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        
        if len(self.content) > 50000:  # 50K characters limit
            raise ValueError(f"Message content too long (max 50000 chars): {len(self.content)}")
        
        # Validate role
        if not isinstance(self.role, MessageRole):
            raise ValueError(f"Invalid message role: {self.role}")
    
    @classmethod
    def create_user_message(
        cls,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Message':
        """Factory method to create a user message."""
        return cls(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=MessageRole.USER,
            content=content,
            created_at=utc_now(),
            metadata=metadata or {}
        )

    @classmethod
    def create_assistant_message(
        cls,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Message':
        """Factory method to create an assistant message."""
        return cls(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=utc_now(),
            metadata=metadata or {}
        )

    @classmethod
    def create_system_message(
        cls,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Message':
        """Factory method to create a system message."""
        return cls(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=MessageRole.SYSTEM,
            content=content,
            created_at=utc_now(),
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "role": str(self.role),
            "content": self.content,
            "created_at": format_iso_utc(self.created_at),
            "metadata": self.metadata or {}
        }

