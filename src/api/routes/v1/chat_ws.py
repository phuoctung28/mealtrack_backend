"""
WebSocket endpoint for real-time chat.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.exceptions import WebSocketException

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ResourceNotFoundException
from src.app.queries.chat import GetThreadQuery
from src.infra.event_bus import EventBus
from src.infra.websocket.connection_manager import chat_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["Chat WebSocket"])


async def verify_thread_access(thread_id: str, user_id: str, event_bus: EventBus) -> bool:
    """Verify user has access to thread."""
    try:
        query = GetThreadQuery(thread_id=thread_id, user_id=user_id)
        await event_bus.send(query)
        return True
    except (ResourceNotFoundException, Exception) as e:
        logger.warning(f"Thread access denied for user {user_id}, thread {thread_id}: {e}")
        return False


@router.websocket("/ws/{thread_id}")
async def chat_websocket(
    websocket: WebSocket,
    thread_id: str,
    user_id: str = Query(...),
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time chat.
    
    Connection URL: ws://localhost:8000/v1/chat/ws/{thread_id}?user_id={user_id}&token={firebase_token}
    
    Message Types (Incoming):
    - ping: Keep-alive ping
    - typing: User is typing indicator
    
    Message Types (Outgoing):
    - message_complete: New message received
    - message_chunk: Streaming message chunk (AI response)
    - typing_indicator: Someone is typing
    - error: Error occurred
    - pong: Response to ping
    """
    # Note: In production, validate the Firebase token here
    # For now, we accept user_id from query params
    
    # Get event bus for thread verification
    from src.api.base_dependencies import get_db
    from src.api.dependencies.event_bus import get_configured_event_bus as get_event_bus_sync
    
    # For WebSocket, we need to handle async dependency injection differently
    # This is a simplified version - in production, implement proper token validation
    
    try:
        # Connect to manager
        await chat_connection_manager.connect(websocket, thread_id, user_id)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "thread_id": thread_id,
            "message": "Connected to chat thread"
        })
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "typing":
                    # Broadcast typing indicator to other users
                    is_typing = message.get("is_typing", False)
                    await chat_connection_manager.broadcast_typing_indicator(
                        thread_id, is_typing
                    )
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            
            except WebSocketDisconnect:
                break
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))
    
    finally:
        # Cleanup on disconnect
        chat_connection_manager.disconnect(websocket, thread_id, user_id)
        logger.info(f"WebSocket closed for thread {thread_id}")

