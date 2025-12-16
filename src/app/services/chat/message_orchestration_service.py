"""
Message orchestration service for coordinating the send message flow.
Handles validation, persistence, AI response, and notifications.
"""
import logging
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.domain.model.chat import Message, ThreadStatus
from src.domain.ports.chat_repository_port import ChatRepositoryPort
from src.domain.ports.ai_chat_service_port import AIChatServicePort
from .ai_response_coordinator import AIResponseCoordinator
from .chat_notification_service import ChatNotificationService

logger = logging.getLogger(__name__)


class MessageOrchestrationService:
    """
    Orchestrates the complete send message flow.

    Responsibilities:
    - Validate thread and user access
    - Save user message
    - Coordinate AI response generation
    - Save assistant message
    - Handle notifications
    - Manage errors
    """

    def __init__(
        self,
        chat_repository: ChatRepositoryPort,
        ai_service: Optional[AIChatServicePort] = None
    ):
        """
        Initialize orchestration service.

        Args:
            chat_repository: Repository for chat operations
            ai_service: Optional AI service for generating responses
        """
        self.chat_repository = chat_repository
        self.ai_service = ai_service

        # Initialize supporting services
        self.notification_service = ChatNotificationService()
        self.ai_coordinator = None

        if ai_service:
            self.ai_coordinator = AIResponseCoordinator(
                ai_service=ai_service,
                notification_service=self.notification_service
            )

    async def send_message(
        self,
        thread_id: str,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message and get AI response.

        Args:
            thread_id: Thread ID
            user_id: User ID
            content: Message content
            metadata: Optional message metadata

        Returns:
            Dictionary with:
            - success: Boolean indicating success
            - user_message: Saved user message data
            - assistant_message: Saved assistant message data (if AI available)
            - ai_error: Error information if AI failed

        Raises:
            ResourceNotFoundException: If thread not found
            ValidationException: If validation fails
        """
        # Validate thread and user access
        thread = self._validate_thread_access(thread_id, user_id)

        # Create and save user message
        user_message = self._save_user_message(thread_id, content, metadata)

        # Notify about user message
        await self.notification_service.notify_message_sent(
            thread_id,
            user_message.to_dict()
        )

        # Generate AI response if service is available
        assistant_message = None
        ai_error = None

        if self.ai_coordinator:
            assistant_message, ai_error = await self._generate_ai_response(
                thread_id,
                user_message
            )

        return {
            "success": True,
            "user_message": user_message.to_dict(),
            "assistant_message": assistant_message.to_dict() if assistant_message else None,
            "ai_error": ai_error
        }

    def _validate_thread_access(self, thread_id: str, user_id: str):
        """
        Validate thread exists and user has access.

        Args:
            thread_id: Thread ID to validate
            user_id: User ID to validate

        Returns:
            Thread domain object

        Raises:
            ResourceNotFoundException: If thread not found
            ValidationException: If user doesn't have access or thread inactive
        """
        # Find thread
        thread = self.chat_repository.find_thread_by_id(thread_id)
        if not thread:
            raise ResourceNotFoundException(
                message="Thread not found",
                details={"thread_id": thread_id}
            )

        # Verify user owns thread
        if thread.user_id != user_id:
            raise ValidationException("User does not have access to this thread")

        # Check thread is active
        if thread.status != ThreadStatus.ACTIVE:
            raise ValidationException("Cannot send message to inactive thread")

        return thread

    def _save_user_message(
        self,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create and save user message.

        Args:
            thread_id: Thread ID
            content: Message content
            metadata: Optional metadata

        Returns:
            Saved Message domain object
        """
        # Create user message
        user_message = Message.create_user_message(
            thread_id=thread_id,
            content=content,
            metadata=metadata
        )

        # Save message
        saved_message = self.chat_repository.save_message(user_message)
        logger.info(
            f"Saved user message {saved_message.message_id} to thread {thread_id}"
        )

        return saved_message

    async def _generate_ai_response(
        self,
        thread_id: str,
        user_message: Message
    ) -> tuple[Optional[Message], Optional[Dict[str, Any]]]:
        """
        Generate and save AI response.

        Args:
            thread_id: Thread ID
            user_message: User message that triggered the response

        Returns:
            Tuple of (assistant_message, error_info)
            - assistant_message: Saved assistant message or None if failed
            - error_info: Error dictionary or None if successful
        """
        try:
            # Get conversation history
            messages = self.chat_repository.find_messages_by_thread(thread_id)

            # Format for AI service
            formatted_messages = [
                {"role": str(msg.role), "content": msg.content}
                for msg in messages
            ]

            # Generate streaming response
            ai_response = await self.ai_coordinator.generate_streaming_response(
                thread_id=thread_id,
                messages=formatted_messages
            )

            # Create assistant message with structured data
            assistant_message = Message.create_assistant_message(
                thread_id=thread_id,
                content=ai_response["message"],
                metadata={
                    **ai_response.get("metadata", {}),
                    "follow_ups": ai_response.get("follow_ups", []),
                    "structured_data": ai_response.get("structured_data")
                }
            )

            # Save assistant message
            saved_message = self.chat_repository.save_message(assistant_message)
            logger.info(
                f"Saved AI response {saved_message.message_id} to thread {thread_id}"
            )

            # Notify about complete message
            await self.notification_service.notify_message_sent(
                thread_id,
                saved_message.to_dict()
            )

            return saved_message, None

        except Exception as e:
            error_info = {
                "message": "Failed to generate AI response",
                "error": str(e),
                "error_type": type(e).__name__
            }

            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return None, error_info
