"""
Handler for creating a new chat thread.
"""
import logging
from typing import Dict, Any

from src.app.commands.chat import CreateThreadCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.chat import Thread, Message
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)

# Welcome message content and follow-ups
WELCOME_MESSAGE_CONTENT = "Hello! I'm your meal planning assistant. What would you like to eat today? Tell me what ingredients you have, and I'll suggest some delicious meals you can cook!"

WELCOME_FOLLOW_UPS = [
    {"id": "quick_1", "text": "I have chicken and vegetables", "type": "question"},
    {"id": "quick_2", "text": "Suggest quick meals (under 30 min)", "type": "question"},
    {"id": "quick_3", "text": "I want healthy low-calorie options", "type": "question"},
    {"id": "quick_4", "text": "What can I make with pasta?", "type": "question"}
]


@handles(CreateThreadCommand)
class CreateThreadCommandHandler(EventHandler[CreateThreadCommand, Dict[str, Any]]):
    """Handler for creating new chat threads."""
    
    def __init__(self, chat_repository: ChatRepositoryPort = None):
        self.chat_repository = chat_repository
    
    def set_dependencies(self, chat_repository: ChatRepositoryPort):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
    
    async def handle(self, command: CreateThreadCommand) -> Dict[str, Any]:
        """Create a new thread with automatic welcome message."""
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
        
        # Create welcome message from assistant
        welcome_message = Message.create_assistant_message(
            thread_id=saved_thread.thread_id,
            content=WELCOME_MESSAGE_CONTENT,
            metadata={
                "is_welcome": True,
                "follow_ups": WELCOME_FOLLOW_UPS,
                "structured_data": None
            }
        )
        
        # Save welcome message
        saved_welcome = self.chat_repository.save_message(welcome_message)
        logger.info(f"Created welcome message {saved_welcome.message_id} for thread {saved_thread.thread_id}")
        
        # Include welcome message in thread response
        thread_dict = saved_thread.to_dict()
        thread_dict["messages"] = [saved_welcome.to_dict()]
        thread_dict["message_count"] = 1
        
        return {
            "success": True,
            "thread": thread_dict,
            "welcome_message": saved_welcome.to_dict()
        }

