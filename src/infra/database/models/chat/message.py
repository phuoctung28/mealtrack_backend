"""
Database model for chat messages.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class ChatMessage(Base, BaseMixin):
    """Database model for chat messages."""
    __tablename__ = 'chat_messages'
    
    # Relationships
    thread_id = Column(String(36), ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Message data
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    
    # JSON metadata for extensibility (tokens, model info, etc.)
    metadata = Column(Text, nullable=True)  # Store as JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    thread = relationship("ChatThread", back_populates="messages")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_chat_messages_thread_created', 'thread_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, thread_id={self.thread_id}, role={self.role})>"
    
    def to_domain(self):
        """Convert database model to domain model."""
        from src.domain.model.chat import Message, MessageRole
        import json
        
        # Parse metadata
        metadata_dict = {}
        if self.metadata:
            try:
                metadata_dict = json.loads(self.metadata)
            except (json.JSONDecodeError, TypeError):
                metadata_dict = {}
        
        # Parse role
        role = MessageRole.USER
        if self.role == 'assistant':
            role = MessageRole.ASSISTANT
        elif self.role == 'system':
            role = MessageRole.SYSTEM
        
        return Message(
            message_id=self.id,
            thread_id=self.thread_id,
            role=role,
            content=self.content,
            created_at=self.created_at,
            metadata=metadata_dict
        )

