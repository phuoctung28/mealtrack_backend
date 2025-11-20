"""
Handler for deleting a chat thread.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.chat import DeleteThreadCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)


@handles(DeleteThreadCommand)
class DeleteThreadCommandHandler(EventHandler[DeleteThreadCommand, Dict[str, Any]]):
    """Handler for deleting chat threads."""
    
    def __init__(self, chat_repository: ChatRepositoryPort = None):
        self.chat_repository = chat_repository
    
    def set_dependencies(self, chat_repository: ChatRepositoryPort):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
    
    async def handle(self, command: DeleteThreadCommand) -> Dict[str, Any]:
        """Delete a thread (soft delete)."""
        if not self.chat_repository:
            raise RuntimeError("Chat repository not configured")
        
        # Find thread
        thread = self.chat_repository.find_thread_by_id(command.thread_id)
        if not thread:
            raise ResourceNotFoundException(
                message="Thread not found",
                details={"thread_id": command.thread_id}
            )
        
        # Verify user owns thread
        if thread.user_id != command.user_id:
            raise ValidationException("User does not have access to this thread")
        
        # Delete thread
        success = self.chat_repository.delete_thread(command.thread_id)
        
        if success:
            logger.info(f"Deleted thread {command.thread_id} for user {command.user_id}")
        
        return {
            "success": success,
            "thread_id": command.thread_id
        }

