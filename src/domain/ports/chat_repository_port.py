"""
Port (interface) for chat repository.
Defines the contract that chat storage implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from src.domain.model.chat import Thread, Message


class ChatRepositoryPort(ABC):
    """Port for chat data persistence."""
    
    @abstractmethod
    def save_thread(self, thread: Thread) -> Thread:
        """Save a thread and return the saved thread."""
        pass
    
    @abstractmethod
    def find_thread_by_id(self, thread_id: str) -> Optional[Thread]:
        """Find a thread by its ID."""
        pass
    
    @abstractmethod
    def find_threads_by_user(
        self,
        user_id: str,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Thread]:
        """Find all threads for a user with pagination."""
        pass
    
    @abstractmethod
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread (soft delete)."""
        pass
    
    @abstractmethod
    def save_message(self, message: Message) -> Message:
        """Save a message and return the saved message."""
        pass
    
    @abstractmethod
    def find_messages_by_thread(
        self,
        thread_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Find all messages for a thread with pagination."""
        pass
    
    @abstractmethod
    def count_user_threads(self, user_id: str, include_deleted: bool = False) -> int:
        """Count total threads for a user."""
        pass
    
    @abstractmethod
    def count_thread_messages(self, thread_id: str) -> int:
        """Count total messages in a thread."""
        pass

