"""
Chat API endpoints - Event-driven architecture.
Handles chat thread and message operations.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.chat_requests import (
    CreateThreadRequest,
    SendMessageRequest
)
from src.api.schemas.response.chat_responses import (
    ThreadResponse,
    ThreadListResponse,
    MessageResponse,
    SendMessageResponse
)
from src.app.commands.chat import (
    CreateThreadCommand,
    SendMessageCommand,
    DeleteThreadCommand
)
from src.app.queries.chat import (
    GetThreadsQuery,
    GetThreadQuery,
    GetMessagesQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/chat", tags=["Chat"])


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Create a new chat thread.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        command = CreateThreadCommand(
            user_id=user_id,
            title=request.title,
            metadata=request.metadata
        )
        
        result = await event_bus.send(command)
        
        return ThreadResponse(**result["thread"])
    
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
    """
    try:
        query = GetThreadQuery(
            thread_id=thread_id,
            user_id=user_id
        )
        
        result = await event_bus.send(query)
        
        # Merge thread and messages into response
        thread_data = result["thread"]
        thread_data["messages"] = result["messages"]
        
        return ThreadResponse(**thread_data)
    
    except Exception as e:
        raise handle_exception(e) from e


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
    """
    try:
        command = SendMessageCommand(
            thread_id=thread_id,
            user_id=user_id,
            content=request.content,
            metadata=request.metadata
        )
        
        result = await event_bus.send(command)
        
        return SendMessageResponse(
            success=result["success"],
            user_message=MessageResponse(**result["user_message"]),
            assistant_message=MessageResponse(**result["assistant_message"]) if result.get("assistant_message") else None
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

