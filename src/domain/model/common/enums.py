"""
Shared enums for domain models.
"""
from enum import Enum


class MessageRole(str, Enum):
    """Role of message sender in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    def __str__(self):
        return self.value
