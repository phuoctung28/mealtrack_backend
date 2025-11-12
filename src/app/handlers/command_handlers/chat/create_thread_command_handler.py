"""
Handler for creating a new chat thread.
"""
import logging
from typing import Dict, Any

from src.app.commands.chat import CreateThreadCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.chat import Thread
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)


@handles(CreateThreadCommand)
class CreateThreadCommandHandler(EventHandler[CreateThreadCommand, Dict[str, Any]]):
    """Handler for creating new chat threads."""
    
    def __init__(self, chat_repository: ChatRepositoryPort = None):
        self.chat_repository = chat_repository
    
    def set_dependencies(self, chat_repository: ChatRepositoryPort):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
    
    async def handle(self, command: CreateThreadCommand) -> Dict[str, Any]:
        """Create a new thread."""
        if not self.chat_repository:
            raise RuntimeError("Chat repository not configured")
        
        # Create new thread domain object
        thread = Thread.create_new(
            user_id=command.user_id,
            title=command.title,
            metadata=command.metadata
        )
        
        # Save thread
        saved_thread = self.chat_repository.save_thread(thread)
        
        logger.info(f"Created new chat thread {saved_thread.thread_id} for user {command.user_id}")
        
        return {
            "success": True,
            "thread": saved_thread.to_dict()
        }

