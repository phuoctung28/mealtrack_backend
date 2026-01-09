"""
Chat message routes - Sending and retrieving messages.
"""
from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.chat_response_builder import ChatResponseBuilder
from src.api.schemas.request.chat_requests import SendMessageRequest
from src.api.schemas.response.chat_responses import SendMessageResponse
from src.app.commands.chat import SendMessageCommand
from src.app.queries.chat import GetMessagesQuery
from src.infra.event_bus import EventBus

router = APIRouter()


@router.post("/threads/{thread_id}/messages", response_model=SendMessageResponse)
async def send_message(
    thread_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Send a message in a thread and get AI response.

    Authentication required: User ID is automatically extracted from the Firebase token.

    The assistant response includes:
    - message: The friendly response text
    - follow_ups: Suggested follow-up questions/actions
    - structured_data: Meal suggestions, recipes, etc.
    """
    try:
        command = SendMessageCommand(
            thread_id=thread_id,
            user_id=user_id,
            content=request.content,
            metadata=request.metadata
        )

        result = await event_bus.send(command)

        # Build responses with proper follow_ups and structured_data
        user_msg = ChatResponseBuilder.build_message_response(result["user_message"])

        assistant_msg = None
        if result.get("assistant_message"):
            assistant_msg = ChatResponseBuilder.build_message_response(
                result["assistant_message"]
            )

        return SendMessageResponse(
            success=result["success"],
            user_message=user_msg,
            assistant_message=assistant_msg
        )

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/threads/{thread_id}/messages")
async def get_messages(
    thread_id: str,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get messages from a thread with pagination.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        query = GetMessagesQuery(
            thread_id=thread_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        result = await event_bus.send(query)

        return result

    except Exception as e:
        raise handle_exception(e) from e
