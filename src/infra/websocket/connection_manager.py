"""
WebSocket connection manager for real-time chat.
Manages active WebSocket connections and message broadcasting.
"""
import asyncio
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
        # Lock to protect connection dictionaries from concurrent modifications
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, thread_id: str, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            # Add to thread connections
            if thread_id not in self.active_connections:
                self.active_connections[thread_id] = set()
            self.active_connections[thread_id].add(websocket)
            
            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected for thread {thread_id}, user {user_id}")
    
    async def _remove_connection(self, websocket: WebSocket):
        """Remove a connection from both dictionaries."""
        async with self._lock:
            # Remove from all thread connections
            threads_to_remove = []
            for thread_id, connections in self.active_connections.items():
                if websocket in connections:
                    connections.discard(websocket)
                    if not connections:
                        threads_to_remove.append(thread_id)
            
            # Clean up empty thread entries
            for thread_id in threads_to_remove:
                del self.active_connections[thread_id]
            
            # Remove from all user connections
            users_to_remove = []
            for user_id, connections in self.user_connections.items():
                if websocket in connections:
                    connections.discard(websocket)
                    if not connections:
                        users_to_remove.append(user_id)
            
            # Clean up empty user entries
            for user_id in users_to_remove:
                del self.user_connections[user_id]
    
    async def disconnect(self, websocket: WebSocket, thread_id: str, user_id: str):
        """Unregister a WebSocket connection."""
        await self._remove_connection(websocket)
        logger.info(f"WebSocket disconnected for thread {thread_id}, user {user_id}")
    
    async def send_to_thread(self, thread_id: str, message: dict):
        """Send a message to all connections subscribed to a thread."""
        # Make a copy of connections to avoid iteration issues during concurrent modifications
        async with self._lock:
            if thread_id not in self.active_connections:
                logger.debug(f"No active connections for thread {thread_id}")
                return
            # Create a copy of the set to iterate over safely
            connections_copy = set(self.active_connections[thread_id])
        
        # Send messages outside the lock to avoid blocking other operations
        disconnected = set()
        for connection in connections_copy:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections from both dictionaries
        for connection in disconnected:
            await self._remove_connection(connection)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all of a user's connections."""
        # Make a copy of connections to avoid iteration issues during concurrent modifications
        async with self._lock:
            if user_id not in self.user_connections:
                logger.debug(f"No active connections for user {user_id}")
                return
            # Create a copy of the set to iterate over safely
            connections_copy = set(self.user_connections[user_id])
        
        # Send messages outside the lock to avoid blocking other operations
        disconnected = set()
        for connection in connections_copy:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections from both dictionaries
        for connection in disconnected:
            await self._remove_connection(connection)
    
    async def broadcast_message_chunk(self, thread_id: str, chunk: str, metadata: dict):
        """Broadcast a streaming message chunk to all thread subscribers."""
        await self.send_to_thread(thread_id, {
            "type": "message_chunk",
            "thread_id": thread_id,
            "chunk": chunk,
            "metadata": metadata
        })
    
    async def broadcast_message_complete(self, thread_id: str, message: dict):
        """
        Broadcast a completed message to all thread subscribers.
        
        Message includes follow_ups and structured_data when available in metadata.
        """
        # Extract structured data from metadata for convenience
        metadata = message.get("metadata", {})
        follow_ups = metadata.get("follow_ups", [])
        structured_data = metadata.get("structured_data")
        
        await self.send_to_thread(thread_id, {
            "type": "message_complete",
            "thread_id": thread_id,
            "message": message,
            "follow_ups": follow_ups,
            "structured_data": structured_data
        })
    
    async def broadcast_structured_data(self, thread_id: str, structured_data: dict):
        """
        Broadcast structured data (follow-ups, meal suggestions) to all thread subscribers.
        
        This is used to send structured data separately from the main message,
        useful for progressive updates during streaming.
        """
        await self.send_to_thread(thread_id, {
            "type": "structured_data",
            "thread_id": thread_id,
            "data": structured_data
        })
    
    async def broadcast_typing_indicator(self, thread_id: str, is_typing: bool):
        """Broadcast typing indicator to all thread subscribers."""
        await self.send_to_thread(thread_id, {
            "type": "typing_indicator",
            "thread_id": thread_id,
            "is_typing": is_typing
        })
    
    async def get_connection_count(self, thread_id: str = None) -> int:
        """Get number of active connections for a thread or total."""
        async with self._lock:
            if thread_id:
                return len(self.active_connections.get(thread_id, set()))
            return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
chat_connection_manager = ConnectionManager()

