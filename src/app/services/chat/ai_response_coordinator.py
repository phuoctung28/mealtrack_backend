"""
AI response coordinator for handling streaming AI responses.
Coordinates AI generation, streaming, and notification.
"""
import logging
from typing import Dict, Any, List, Optional

from src.domain.ports.ai_chat_service_port import AIChatServicePort
from src.infra.services.ai.parsers import AIResponseParser
from .chat_notification_service import ChatNotificationService

logger = logging.getLogger(__name__)


class AIResponseCoordinator:
    """
    Coordinates AI response generation with streaming and notifications.

    Responsibilities:
    - Generate streaming AI responses
    - Broadcast chunks via notifications
    - Parse final structured response
    - Handle errors gracefully
    """

    def __init__(
        self,
        ai_service: AIChatServicePort,
        notification_service: ChatNotificationService,
        parser: Optional[AIResponseParser] = None
    ):
        """
        Initialize coordinator.

        Args:
            ai_service: AI chat service for generating responses
            notification_service: Service for broadcasting notifications
            parser: Parser for AI responses (uses default if None)
        """
        self.ai_service = ai_service
        self.notification_service = notification_service
        self.parser = parser or AIResponseParser()

    async def generate_streaming_response(
        self,
        thread_id: str,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate streaming AI response with real-time notifications.

        Args:
            thread_id: Thread ID for notifications
            messages: Conversation history
            system_prompt: Optional custom system prompt
            temperature: AI temperature parameter

        Returns:
            Dictionary with:
            - content: Full response content
            - message: Parsed display message
            - follow_ups: Parsed follow-up questions
            - structured_data: Parsed structured data
            - metadata: Response metadata

        Raises:
            RuntimeError: If AI generation fails
        """
        # Start typing indicator
        await self.notification_service.notify_typing_indicator(thread_id, True)

        try:
            full_content = ""
            metadata = {}

            # Stream response chunks
            async for chunk_data in self.ai_service.generate_streaming_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature
            ):
                chunk = chunk_data.get("chunk", "")
                metadata = chunk_data.get("metadata", {})

                if chunk:
                    full_content += chunk

                    # Broadcast chunk
                    await self.notification_service.notify_message_chunk(
                        thread_id,
                        chunk,
                        metadata
                    )

            # Stop typing indicator
            await self.notification_service.notify_typing_indicator(thread_id, False)

            # Parse complete response
            parsed_response = self.parser.parse_response(full_content.strip())

            return {
                "content": full_content.strip(),
                "message": parsed_response.get("message", full_content.strip()),
                "follow_ups": parsed_response.get("follow_ups", []),
                "structured_data": parsed_response.get("structured_data"),
                "metadata": metadata
            }

        except Exception as e:
            # Stop typing indicator on error
            await self.notification_service.notify_typing_indicator(thread_id, False)

            # Notify about error
            await self.notification_service.notify_error(
                thread_id,
                "Failed to generate AI response",
                type(e).__name__
            )

            logger.error(f"Error generating AI response: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate AI response: {str(e)}")

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate non-streaming AI response (for testing or batch operations).

        Args:
            messages: Conversation history
            system_prompt: Optional custom system prompt
            temperature: AI temperature parameter

        Returns:
            Dictionary with parsed response data

        Raises:
            RuntimeError: If AI generation fails
        """
        try:
            response = await self.ai_service.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature
            )

            content = response.get("content", "")
            parsed_response = self.parser.parse_response(content)

            return {
                "content": content,
                "message": parsed_response.get("message", content),
                "follow_ups": parsed_response.get("follow_ups", []),
                "structured_data": parsed_response.get("structured_data"),
                "metadata": response.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate AI response: {str(e)}")
