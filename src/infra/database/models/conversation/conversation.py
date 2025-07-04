"""
Conversation model for tracking chat conversations with users.
"""
from sqlalchemy import Column, String, JSON, Enum
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin
from src.infra.database.models.enums import ConversationStateEnum


class Conversation(Base, BaseMixin):
    """Tracks chat conversations and their state."""
    __tablename__ = "conversations"
    
    user_id = Column(String(255), nullable=False, index=True)
    state = Column(Enum(ConversationStateEnum), nullable=False)
    
    # Conversation context stored as JSON
    context = Column(JSON)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")