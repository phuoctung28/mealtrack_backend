"""
WebSocket connection manager for real-time chat.
Manages active WebSocket connections and message broadcasting.
"""
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        # Map of thread_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of user_id -> set of active WebSocket connections (for user-level broadcasts)
        self.user_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, thread_id: str, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        # Add to thread connections
        if thread_id not in self.active_connections:
            self.active_connections[thread_id] = set()
        self.active_connections[thread_id].add(websocket)
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected for thread {thread_id}, user {user_id}")
    
    def disconnect(self, websocket: WebSocket, thread_id: str, user_id: str):
        """Unregister a WebSocket connection."""
        # Remove from thread connections
        if thread_id in self.active_connections:
            self.active_connections[thread_id].discard(websocket)
            if not self.active_connections[thread_id]:
                del self.active_connections[thread_id]
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected for thread {thread_id}, user {user_id}")
    
    async def send_to_thread(self, thread_id: str, message: dict):
        """Send a message to all connections subscribed to a thread."""
        if thread_id not in self.active_connections:
            logger.debug(f"No active connections for thread {thread_id}")
            return
        
        disconnected = set()
        for connection in self.active_connections[thread_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.active_connections[thread_id].discard(connection)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all of a user's connections."""
        if user_id not in self.user_connections:
            logger.debug(f"No active connections for user {user_id}")
            return
        
        disconnected = set()
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.user_connections[user_id].discard(connection)
    
    async def broadcast_message_chunk(self, thread_id: str, chunk: str, metadata: dict):
        """Broadcast a streaming message chunk to all thread subscribers."""
        await self.send_to_thread(thread_id, {
            "type": "message_chunk",
            "thread_id": thread_id,
            "chunk": chunk,
            "metadata": metadata
        })
    
    async def broadcast_message_complete(self, thread_id: str, message: dict):
        """Broadcast a completed message to all thread subscribers."""
        await self.send_to_thread(thread_id, {
            "type": "message_complete",
            "thread_id": thread_id,
            "message": message
        })
    
    async def broadcast_typing_indicator(self, thread_id: str, is_typing: bool):
        """Broadcast typing indicator to all thread subscribers."""
        await self.send_to_thread(thread_id, {
            "type": "typing_indicator",
            "thread_id": thread_id,
            "is_typing": is_typing
        })
    
    def get_connection_count(self, thread_id: str = None) -> int:
        """Get number of active connections for a thread or total."""
        if thread_id:
            return len(self.active_connections.get(thread_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
chat_connection_manager = ConnectionManager()

