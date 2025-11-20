"""
Handler for sending a message in a chat thread.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.chat import SendMessageCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.chat import Message, ThreadStatus
from src.domain.ports.chat_repository_port import ChatRepositoryPort
from src.domain.ports.ai_chat_service_port import AIChatServicePort

logger = logging.getLogger(__name__)


# Import WebSocket manager (optional dependency)
try:
    from src.infra.websocket import chat_connection_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket connection manager not available")


@handles(SendMessageCommand)
class SendMessageCommandHandler(EventHandler[SendMessageCommand, Dict[str, Any]]):
    """Handler for sending messages in chat threads."""
    
    def __init__(
        self,
        chat_repository: ChatRepositoryPort = None,
        ai_service: AIChatServicePort = None
    ):
        self.chat_repository = chat_repository
        self.ai_service = ai_service
    
    def set_dependencies(
        self,
        chat_repository: ChatRepositoryPort,
        ai_service: AIChatServicePort = None
    ):
        """Set dependencies for dependency injection."""
        self.chat_repository = chat_repository
        self.ai_service = ai_service
    
    async def handle(self, command: SendMessageCommand) -> Dict[str, Any]:
        """Send a message and get AI response."""
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
        
        # Check thread is active
        if thread.status != ThreadStatus.ACTIVE:
            raise ValidationException("Cannot send message to inactive thread")
        
        # Create user message
        user_message = Message.create_user_message(
            thread_id=command.thread_id,
            content=command.content,
            metadata=command.metadata
        )
        
        # Save user message
        saved_user_message = self.chat_repository.save_message(user_message)
        logger.info(f"Saved user message {saved_user_message.message_id} to thread {command.thread_id}")
        
        # Broadcast user message via WebSocket
        if WEBSOCKET_AVAILABLE:
            await chat_connection_manager.broadcast_message_complete(
                command.thread_id,
                saved_user_message.to_dict()
            )
        
        # Generate AI response with streaming
        assistant_message = None
        ai_error = None
        if self.ai_service:
            try:
                # Get conversation history
                messages = self.chat_repository.find_messages_by_thread(command.thread_id)
                
                # Format messages for AI service
                formatted_messages = [
                    {"role": str(msg.role), "content": msg.content}
                    for msg in messages
                ]
                
                # Broadcast typing indicator
                if WEBSOCKET_AVAILABLE:
                    await chat_connection_manager.broadcast_typing_indicator(
                        command.thread_id, True
                    )
                
                # Stream AI response
                full_content = ""
                metadata = {}
                
                async for chunk_data in self.ai_service.generate_streaming_response(formatted_messages):
                    chunk = chunk_data.get("chunk", "")
                    full_content += chunk
                    metadata = chunk_data.get("metadata", {})
                    
                    # Broadcast chunk via WebSocket
                    if WEBSOCKET_AVAILABLE and chunk:
                        await chat_connection_manager.broadcast_message_chunk(
                            command.thread_id,
                            chunk,
                            metadata
                        )
                
                # Stop typing indicator
                if WEBSOCKET_AVAILABLE:
                    await chat_connection_manager.broadcast_typing_indicator(
                        command.thread_id, False
                    )
                
                # Create and save assistant message
                assistant_message = Message.create_assistant_message(
                    thread_id=command.thread_id,
                    content=full_content.strip(),
                    metadata=metadata
                )
                
                assistant_message = self.chat_repository.save_message(assistant_message)
                logger.info(f"Saved AI response {assistant_message.message_id} to thread {command.thread_id}")
                
                # Broadcast complete message via WebSocket
                if WEBSOCKET_AVAILABLE:
                    await chat_connection_manager.broadcast_message_complete(
                        command.thread_id,
                        assistant_message.to_dict()
                    )
            
            except Exception as e:
                logger.error(f"Error generating AI response: {e}", exc_info=True)
                # Stop typing indicator on error
                if WEBSOCKET_AVAILABLE:
                    await chat_connection_manager.broadcast_typing_indicator(
                        command.thread_id, False
                    )
                # Store error information - user message was successfully saved
                ai_error = {
                    "message": "Failed to generate AI response",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        return {
            "success": True,
            "user_message": saved_user_message.to_dict(),
            "assistant_message": assistant_message.to_dict() if assistant_message else None,
            "ai_error": ai_error
        }

