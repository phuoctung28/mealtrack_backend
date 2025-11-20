"""
WebSocket endpoint for real-time chat.
"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.exceptions import WebSocketException
from firebase_admin import auth as firebase_auth

from src.api.exceptions import ResourceNotFoundException
from src.app.queries.chat import GetThreadQuery
from src.infra.database.config import get_db
from src.infra.event_bus import EventBus
from src.infra.websocket.connection_manager import chat_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["Chat WebSocket"])


async def verify_firebase_token_and_get_user_id(token: str) -> str:
    """
    Verify Firebase token and return the authenticated user's database ID.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        The authenticated user's database ID (UUID)
        
    Raises:
        WebSocketException: If token is invalid, expired, or user not found
    """
    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(token)
        firebase_uid = decoded_token.get("uid")
        
        if not firebase_uid:
            logger.error("Firebase token missing 'uid' field")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token: missing user identifier"
            )
        
        # Look up user in database by firebase_uid (only active users)
        from src.infra.database.models.user.user import User
        db = next(get_db())
        try:
            user = db.query(User).filter(
                User.firebase_uid == firebase_uid,
                User.is_active == True  # CRITICAL: Block deleted/inactive users
            ).first()
            
            if not user:
                logger.warning(f"Active user with Firebase UID {firebase_uid} not found in database")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User not found or account has been deleted"
                )
            
            return user.id
        finally:
            db.close()
            
    except WebSocketException:
        raise
    except firebase_auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token has expired"
        ) from e
    except firebase_auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked Firebase token: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token has been revoked"
        ) from e
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token"
        ) from e
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Failed to verify authentication token"
        ) from e


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
    token: str = Query(...),
    event_bus: EventBus = None,
):
    """
    WebSocket endpoint for real-time chat.
    
    Connection URL: ws://localhost:8000/v1/chat/ws/{thread_id}?token={firebase_token}
    
    The Firebase token is validated and the user_id is extracted from it.
    The user_id is NOT accepted as a query parameter for security reasons.
    
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
    user_id = None
    
    try:
        # Validate Firebase token and extract user_id
        user_id = await verify_firebase_token_and_get_user_id(token)
        logger.info(f"WebSocket authentication successful for user {user_id}, thread {thread_id}")
        
        # Verify user has access to thread (if event_bus is available)
        if event_bus:
            has_access = await verify_thread_access(thread_id, user_id, event_bus)
            if not has_access:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Access denied to this thread"
                )
        
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
    
    except WebSocketException:
        # Re-raise WebSocket exceptions (authentication/authorization errors)
        raise
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))
    
    finally:
        # Cleanup on disconnect (only if user_id was successfully authenticated)
        if user_id:
            await chat_connection_manager.disconnect(websocket, thread_id, user_id)
            logger.info(f"WebSocket closed for thread {thread_id}, user {user_id}")

