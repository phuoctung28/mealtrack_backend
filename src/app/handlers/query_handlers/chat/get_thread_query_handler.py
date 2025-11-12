"""
Handler for getting a single thread by ID.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.events.base import EventHandler, handles
from src.app.queries.chat import GetThreadQuery
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)


@handles(GetThreadQuery)
class GetThreadQueryHandler(EventHandler[GetThreadQuery, Dict[str, Any]]):
    """Handler for getting a single thread."""
    
    def __init__(self, chat_repository: ChatRepositoryPort = None):
        self.chat_repository = chat_repository
    
    def set_dependencies(self, chat_repository: ChatRepositoryPort):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
    
    async def handle(self, query: GetThreadQuery) -> Dict[str, Any]:
        """Get a thread by ID."""
        if not self.chat_repository:
            raise RuntimeError("Chat repository not configured")
        
        # Find thread
        thread = self.chat_repository.find_thread_by_id(query.thread_id)
        if not thread:
            raise ResourceNotFoundException(
                message="Thread not found",
                details={"thread_id": query.thread_id}
            )
        
        # Verify user owns thread
        if thread.user_id != query.user_id:
            raise ValidationException("User does not have access to this thread")
        
        # Get messages
        messages = self.chat_repository.find_messages_by_thread(query.thread_id)
        
        return {
            "thread": thread.to_dict(),
            "messages": [msg.to_dict() for msg in messages],
            "message_count": len(messages)
        }

