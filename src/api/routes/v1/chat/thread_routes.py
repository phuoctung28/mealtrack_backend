"""
Chat thread routes - Thread CRUD operations.
"""
from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.chat_response_builder import ChatResponseBuilder
from src.api.schemas.request.chat_requests import CreateThreadRequest
from src.api.schemas.response.chat_responses import (
    ThreadResponse,
    ThreadListResponse
)
from src.app.commands.chat import CreateThreadCommand, DeleteThreadCommand
from src.app.queries.chat import GetThreadsQuery, GetThreadQuery
from src.infra.event_bus import EventBus

router = APIRouter()


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Create a new chat thread with automatic welcome message.

    Authentication required: User ID is automatically extracted from the Firebase token.

    Returns the thread with a welcome message from the meal planning assistant,
    including suggested follow-up questions to help users get started.
    """
    try:
        command = CreateThreadCommand(
            user_id=user_id,
            title=request.title,
            metadata=request.metadata
        )

        result = await event_bus.send(command)

        # Build thread response with properly structured messages
        thread_data = ChatResponseBuilder.build_thread_with_messages(
            thread_data=result["thread"],
            messages=result["thread"].get("messages")
        )

        return ThreadResponse(**thread_data)

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/threads", response_model=ThreadListResponse)
async def get_threads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_deleted: bool = Query(False),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get list of chat threads for the current user.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        query = GetThreadsQuery(
            user_id=user_id,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )

        result = await event_bus.send(query)

        return ThreadListResponse(**result)

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get a specific thread with its messages.

    Authentication required: User ID is automatically extracted from the Firebase token.

    Messages include follow_ups and structured_data when available.
    """
    try:
        query = GetThreadQuery(
            thread_id=thread_id,
            user_id=user_id
        )

        result = await event_bus.send(query)

        # Build thread response with properly structured messages
        thread_data = ChatResponseBuilder.build_thread_with_messages(
            thread_data=result["thread"],
            messages=result.get("messages", [])
        )

        return ThreadResponse(**thread_data)

    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Delete a thread (soft delete).

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        command = DeleteThreadCommand(
            thread_id=thread_id,
            user_id=user_id
        )

        result = await event_bus.send(command)

        return result

    except Exception as e:
        raise handle_exception(e) from e
