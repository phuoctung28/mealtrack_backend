"""
Handler for sending a message in a chat thread.
Refactored to use MessageOrchestrationService.
"""
import logging
from typing import Dict, Any

from src.app.commands.chat import SendMessageCommand
from src.app.events.base import EventHandler, handles
from src.app.services.chat import MessageOrchestrationService
from src.domain.ports.ai_chat_service_port import AIChatServicePort
from src.domain.ports.chat_repository_port import ChatRepositoryPort

logger = logging.getLogger(__name__)


@handles(SendMessageCommand)
class SendMessageCommandHandler(EventHandler[SendMessageCommand, Dict[str, Any]]):
    """
    Handler for sending messages in chat threads.
    
    This handler is now a thin coordinator that delegates to
    MessageOrchestrationService for the actual work.
    """
    
    def __init__(
        self,
        chat_repository: ChatRepositoryPort = None,
        ai_service: AIChatServicePort = None
    ):
        self.chat_repository = chat_repository
        self.ai_service = ai_service
        
        # Initialize orchestration service immediately if dependencies are provided
        if chat_repository:
            self.orchestration_service = MessageOrchestrationService(
                chat_repository=chat_repository,
                ai_service=ai_service
            )
        else:
            self.orchestration_service = None
    
    def set_dependencies(
        self,
        chat_repository: ChatRepositoryPort,
        ai_service: AIChatServicePort = None
    ):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
        self.ai_service = ai_service
        
        # Initialize orchestration service with dependencies
        if chat_repository:
            self.orchestration_service = MessageOrchestrationService(
                chat_repository=chat_repository,
                ai_service=ai_service
            )
    
    async def handle(self, command: SendMessageCommand) -> Dict[str, Any]:
        """
        Send a message and get AI response.
        
        Delegates to MessageOrchestrationService for processing.
        """
        if not self.orchestration_service:
            raise RuntimeError("Orchestration service not configured")
        
        return await self.orchestration_service.send_message(
            thread_id=command.thread_id,
            user_id=command.user_id,
            content=command.content,
            metadata=command.metadata
        )

