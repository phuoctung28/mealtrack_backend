"""RQ task functions for chat AI responses."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.api.mappers.chat_response_builder import ChatResponseBuilder
from src.app.commands.chat import SendMessageCommand
from src.infra.tasks._rq_async import run_async

logger = logging.getLogger(__name__)


def send_chat_message_task(
    *,
    thread_id: str,
    user_id: str,
    content: str,
    metadata: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Send a message and return SendMessageResponse-compatible dict."""
    logger.info(
        "RQ task: send_chat_message_task started (thread_id=%s, user_id=%s)",
        thread_id,
        user_id,
    )

    from src.api.base_dependencies import initialize_cache_layer

    run_async(initialize_cache_layer())

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()
    command = SendMessageCommand(
        thread_id=thread_id,
        user_id=user_id,
        content=content,
        metadata=metadata,
    )

    result = run_async(event_bus.send(command))

    user_msg = ChatResponseBuilder.build_message_response(result["user_message"])
    assistant_msg = None
    if result.get("assistant_message"):
        assistant_msg = ChatResponseBuilder.build_message_response(result["assistant_message"])

    return {
        "success": result["success"],
        "user_message": user_msg,
        "assistant_message": assistant_msg,
    }

