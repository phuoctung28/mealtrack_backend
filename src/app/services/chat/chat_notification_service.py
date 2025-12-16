"""
Chat notification service for broadcasting messages via WebSocket.
Abstracts notification logic from command handlers.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChatNotificationService:
    """
    Handles all chat-related notifications via WebSocket.

    This service abstracts WebSocket broadcasting from command handlers,
    making it easier to:
    - Add alternative notification channels (push notifications, email, etc.)
    - Handle broadcast failures gracefully
    - Test handlers without WebSocket dependencies
    """

    def __init__(self):
        """Initialize notification service with optional WebSocket manager."""
        self.websocket_manager = None
        self._websocket_available = False

        # Try to import WebSocket manager
        try:
            from src.infra.websocket import chat_connection_manager
            self.websocket_manager = chat_connection_manager
            self._websocket_available = True
            logger.info("WebSocket notifications enabled")
        except ImportError:
            logger.warning("WebSocket connection manager not available")

    def is_websocket_available(self) -> bool:
        """Check if WebSocket notifications are available."""
        return self._websocket_available

    async def notify_message_sent(
        self,
        thread_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        Notify subscribers that a message was sent.

        Args:
            thread_id: Thread ID
            message: Message data dictionary
        """
        if not self._websocket_available:
            return

        try:
            await self.websocket_manager.broadcast_message_complete(
                thread_id,
                message
            )
        except Exception as e:
            logger.error(f"Failed to broadcast message notification: {e}")

    async def notify_typing_indicator(
        self,
        thread_id: str,
        is_typing: bool
    ) -> None:
        """
        Notify subscribers of typing indicator status.

        Args:
            thread_id: Thread ID
            is_typing: Whether assistant is typing
        """
        if not self._websocket_available:
            return

        try:
            await self.websocket_manager.broadcast_typing_indicator(
                thread_id,
                is_typing
            )
        except Exception as e:
            logger.error(f"Failed to broadcast typing indicator: {e}")

    async def notify_message_chunk(
        self,
        thread_id: str,
        chunk: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Notify subscribers of a streaming message chunk.

        Args:
            thread_id: Thread ID
            chunk: Text chunk
            metadata: Optional chunk metadata
        """
        if not self._websocket_available:
            return

        try:
            await self.websocket_manager.broadcast_message_chunk(
                thread_id,
                chunk,
                metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to broadcast message chunk: {e}")

    async def notify_error(
        self,
        thread_id: str,
        error_message: str,
        error_type: Optional[str] = None
    ) -> None:
        """
        Notify subscribers of an error.

        Args:
            thread_id: Thread ID
            error_message: Error message
            error_type: Optional error type
        """
        if not self._websocket_available:
            return

        try:
            await self.websocket_manager.send_to_thread(thread_id, {
                "type": "error",
                "thread_id": thread_id,
                "message": error_message,
                "error_type": error_type
            })
        except Exception as e:
            logger.error(f"Failed to broadcast error notification: {e}")
