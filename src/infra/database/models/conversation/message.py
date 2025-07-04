"""
Conversation message model for individual messages within a conversation.
"""
from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class ConversationMessage(Base, SecondaryEntityMixin):
    """Individual messages within a conversation."""
    __tablename__ = "conversation_messages"
    
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")