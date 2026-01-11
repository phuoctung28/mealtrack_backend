"""
Database model for chat threads.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.domain.services.timezone_utils import utc_now
from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class ChatThread(Base, BaseMixin):
    """Database model for conversation threads."""
    __tablename__ = 'chat_threads'
    
    # Relationships
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    
    # Thread metadata
    title = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default='active', index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # JSON metadata for extensibility (use metadata_ to avoid SQLAlchemy reserved word)
    metadata_ = Column('metadata', Text, nullable=True)  # Store as JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    user = relationship("User", backref="chat_threads")
    messages = relationship(
        "ChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    
    def __repr__(self):
        return f"<ChatThread(id={self.id}, user_id={self.user_id}, title={self.title})>"
    
    def to_domain(self):
        """Convert database model to domain model."""
        from src.domain.model.chat import Thread, ThreadStatus
        import json
        
        # Parse metadata
        metadata_dict = {}
        if self.metadata_:
            try:
                metadata_dict = json.loads(self.metadata_)
            except (json.JSONDecodeError, TypeError):
                metadata_dict = {}
        
        # Parse status
        status = ThreadStatus.ACTIVE
        if self.status == 'archived':
            status = ThreadStatus.ARCHIVED
        elif self.status == 'deleted':
            status = ThreadStatus.DELETED
        
        # Convert messages if loaded
        messages = []
        if hasattr(self, 'messages') and self.messages:
            messages = [msg.to_domain() for msg in self.messages]
        
        return Thread(
            thread_id=self.id,
            user_id=self.user_id,
            title=self.title,
            status=status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=metadata_dict,
            messages=messages
        )

