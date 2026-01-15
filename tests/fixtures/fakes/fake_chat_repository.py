"""Fake chat repository for testing."""
from typing import List, Optional
from uuid import UUID

from src.domain.model.chat import Thread, Message
from src.domain.ports.chat_repository_port import ChatRepositoryPort


class FakeChatRepository(ChatRepositoryPort):
    """In-memory implementation of ChatRepositoryPort for testing."""
    
    def __init__(self):
        self._threads: dict[str, Thread] = {}
        self._messages: dict[str, Message] = {}
    
    def save_thread(self, thread: Thread) -> Thread:
        """Save a thread."""
        self._threads[thread.id] = thread
        return thread
    
    def find_thread_by_id(self, thread_id: str) -> Optional[Thread]:
        """Find a thread by ID."""
        return self._threads.get(thread_id)
    
    def find_threads_by_user(self, user_id: UUID, limit: int = 50) -> List[Thread]:
        """Find all threads for a user."""
        return [
            thread for thread in self._threads.values()
            if thread.user_id == str(user_id)
        ][:limit]
    
    def save_message(self, message: Message) -> Message:
        """Save a message."""
        self._messages[message.id] = message
        return message
    
    def find_message_by_id(self, message_id: str) -> Optional[Message]:
        """Find a message by ID."""
        return self._messages.get(message_id)
    
    def find_messages_by_thread(self, thread_id: str, limit: int = 100) -> List[Message]:
        """Find all messages in a thread."""
        return [
            message for message in self._messages.values()
            if message.thread_id == thread_id
        ][:limit]
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread."""
        if thread_id in self._threads:
            # Also delete associated messages
            message_ids = [
                msg_id for msg_id, msg in self._messages.items()
                if msg.thread_id == thread_id
            ]
            for msg_id in message_ids:
                del self._messages[msg_id]
            
            del self._threads[thread_id]
            return True
        return False
    
    def count_user_threads(self, user_id: UUID) -> int:
        """Count total threads for a user."""
        return len([
            thread for thread in self._threads.values()
            if thread.user_id == str(user_id)
        ])
    
    def count_thread_messages(self, thread_id: str) -> int:
        """Count total messages in a thread."""
        return len([
            message for message in self._messages.values()
            if message.thread_id == thread_id
        ])
