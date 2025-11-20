"""
Enums for chat domain models.
"""
from enum import Enum


class MessageRole(str, Enum):
    """Role of message sender in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"  # For system prompts/instructions
    
    def __str__(self):
        return self.value


class ThreadStatus(str, Enum):
    """Status of a conversation thread."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    
    def __str__(self):
        return self.value

