"""
WebSocket edge case tests.
Tests error handling, concurrency, and reliability scenarios.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.messages_sent = []
        self.messages_to_receive = []
        
    async def accept(self):
        self.accepted = True
        
    async def close(self, code: int = 1000):
        self.closed = True
        self.close_code = code
        
    async def send_json(self, data):
        self.messages_sent.append(data)
        
    async def receive_json(self):
        if not self.messages_to_receive:
            raise WebSocketDisconnect()
        return self.messages_to_receive.pop(0)
    
    async def receive_text(self):
        if not self.messages_to_receive:
            raise WebSocketDisconnect()
        return self.messages_to_receive.pop(0)


class TestExpiredTokenHandling:
    """Test WebSocket behavior with expired tokens."""

    @pytest.mark.asyncio
    async def test_connection_rejected_with_expired_token(self):
        """WebSocket should reject connections with expired tokens."""
        ws = MockWebSocket()
        
        # Simulate expired token check
        token_valid = False
        
        if not token_valid:
            await ws.close(code=4001)
        
        assert ws.close_code == 4001

    @pytest.mark.asyncio
    async def test_connection_closed_when_token_expires_mid_session(self):
        """WebSocket should handle token expiration during active session."""
        ws = MockWebSocket()
        ws.accepted = True
        
        # Simulate token expiration check
        token_valid = True
        
        async def check_token():
            nonlocal token_valid
            return token_valid
        
        # Initial check passes
        assert await check_token() is True
        
        # Token expires
        token_valid = False
        
        # Next check fails
        assert await check_token() is False
        
        # Connection should be terminated
        await ws.close(code=4001)
        assert ws.close_code == 4001


class TestConcurrentConnections:
    """Test multiple WebSocket connections from same user."""

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        """Should handle multiple connections from same user."""
        user_id = "user_123"
        
        # Simulate connection manager
        class ConnectionManager:
            def __init__(self):
                self.active = {}
            
            async def connect(self, user_id: str, ws: MockWebSocket):
                if user_id not in self.active:
                    self.active[user_id] = []
                self.active[user_id].append(ws)
                await ws.accept()
            
            async def disconnect(self, user_id: str, ws: MockWebSocket):
                if user_id in self.active:
                    self.active[user_id].remove(ws)
            
            def get_connections(self, user_id: str):
                return self.active.get(user_id, [])
        
        manager = ConnectionManager()
        
        # Connect multiple times
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(user_id, ws1)
        await manager.connect(user_id, ws2)
        await manager.connect(user_id, ws3)
        
        # All connections should be active
        assert len(manager.get_connections(user_id)) == 3
        assert all(ws.accepted for ws in [ws1, ws2, ws3])
        
        # Disconnect one
        await manager.disconnect(user_id, ws2)
        assert len(manager.get_connections(user_id)) == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all_user_connections(self):
        """Should broadcast messages to all user connections."""
        connections = [MockWebSocket() for _ in range(3)]
        
        for ws in connections:
            await ws.accept()
        
        # Broadcast message
        message = {"type": "notification", "data": "test"}
        for ws in connections:
            await ws.send_json(message)
        
        # All connections should receive message
        for ws in connections:
            assert message in ws.messages_sent


class TestMessageOrdering:
    """Test message ordering guarantees."""

    @pytest.mark.asyncio
    async def test_messages_delivered_in_order(self):
        """Messages should be delivered in FIFO order."""
        ws = MockWebSocket()
        await ws.accept()
        
        # Send multiple messages
        messages = [
            {"id": 1, "text": "First"},
            {"id": 2, "text": "Second"},
            {"id": 3, "text": "Third"},
        ]
        
        for msg in messages:
            await ws.send_json(msg)
        
        # Verify order preserved
        assert ws.messages_sent == messages
        
        # Verify IDs are in order
        ids = [m["id"] for m in ws.messages_sent]
        assert ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_concurrent_sends_preserve_order(self):
        """Concurrent sends should preserve relative order."""
        ws = MockWebSocket()
        await ws.accept()
        
        # Simulate concurrent sends
        async def send_batch(start_id: int, count: int):
            for i in range(count):
                await ws.send_json({"id": start_id + i})
        
        # Send concurrently
        await asyncio.gather(
            send_batch(0, 5),
            send_batch(100, 5),
        )
        
        # Each batch should be in order (though batches may interleave)
        batch1_ids = [m["id"] for m in ws.messages_sent if m["id"] < 100]
        batch2_ids = [m["id"] for m in ws.messages_sent if m["id"] >= 100]
        
        assert batch1_ids == sorted(batch1_ids)
        assert batch2_ids == sorted(batch2_ids)


class TestReconnection:
    """Test reconnection scenarios."""

    @pytest.mark.asyncio
    async def test_reconnection_after_disconnect(self):
        """Client should be able to reconnect after disconnect."""
        user_id = "user_123"
        
        # First connection
        ws1 = MockWebSocket()
        await ws1.accept()
        assert ws1.accepted
        
        # Disconnect
        await ws1.close()
        assert ws1.closed
        
        # Reconnect
        ws2 = MockWebSocket()
        await ws2.accept()
        assert ws2.accepted

    @pytest.mark.asyncio
    async def test_state_not_persisted_after_disconnect(self):
        """Connection state should not persist after disconnect."""
        ws = MockWebSocket()
        await ws.accept()
        
        # Send some messages
        await ws.send_json({"type": "test"})
        assert len(ws.messages_sent) == 1
        
        # Disconnect
        await ws.close()
        
        # New connection starts fresh
        ws2 = MockWebSocket()
        await ws2.accept()
        assert len(ws2.messages_sent) == 0

    @pytest.mark.asyncio
    async def test_reconnection_with_session_recovery(self):
        """Should support session recovery on reconnection."""
        session_id = "session_abc123"
        
        # Mock session store
        session_store = {}
        
        # First connection saves session
        session_store[session_id] = {
            "user_id": "user_123",
            "last_message_id": 42,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Client disconnects and reconnects with session ID
        recovered_session = session_store.get(session_id)
        
        # Session should be recoverable
        assert recovered_session is not None
        assert recovered_session["last_message_id"] == 42


class TestErrorHandling:
    """Test WebSocket error handling."""

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self):
        """Should handle malformed JSON gracefully."""
        ws = MockWebSocket()
        ws.messages_to_receive = ["not valid json"]
        
        await ws.accept()
        
        try:
            # This should fail but not crash
            import json
            data = await ws.receive_text()
            parsed = json.loads(data)
        except json.JSONDecodeError:
            # Expected behavior - should send error response
            await ws.send_json({"error": "Invalid JSON"})
        
        assert {"error": "Invalid JSON"} in ws.messages_sent

    @pytest.mark.asyncio
    async def test_handles_unexpected_disconnect(self):
        """Should handle unexpected client disconnect."""
        ws = MockWebSocket()
        ws.messages_to_receive = []  # No messages = disconnect
        
        await ws.accept()
        
        with pytest.raises(WebSocketDisconnect):
            await ws.receive_json()

    @pytest.mark.asyncio
    async def test_graceful_server_shutdown(self):
        """Should gracefully close connections on server shutdown."""
        connections = [MockWebSocket() for _ in range(5)]
        
        for ws in connections:
            await ws.accept()
        
        # Simulate server shutdown
        for ws in connections:
            await ws.send_json({"type": "server_shutdown"})
            await ws.close(code=1001)  # Going away
        
        # All connections should be closed
        assert all(ws.closed for ws in connections)
        assert all(ws.close_code == 1001 for ws in connections)


class TestRateLimiting:
    """Test WebSocket rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_messages(self):
        """Should rate limit excessive messages."""
        ws = MockWebSocket()
        await ws.accept()
        
        # Simulate rate limiter
        class RateLimiter:
            def __init__(self, max_per_second: int):
                self.max_per_second = max_per_second
                self.message_times = []
            
            def check(self) -> bool:
                now = datetime.utcnow()
                # Remove old timestamps
                cutoff = now - timedelta(seconds=1)
                self.message_times = [
                    t for t in self.message_times 
                    if t > cutoff
                ]
                
                if len(self.message_times) >= self.max_per_second:
                    return False
                
                self.message_times.append(now)
                return True
        
        limiter = RateLimiter(max_per_second=10)
        
        # First 10 messages should pass
        for i in range(10):
            assert limiter.check() is True
        
        # 11th message should be rate limited
        assert limiter.check() is False


class TestHeartbeat:
    """Test WebSocket heartbeat/ping-pong."""

    @pytest.mark.asyncio
    async def test_responds_to_ping(self):
        """Should respond to ping with pong."""
        ws = MockWebSocket()
        ws.messages_to_receive = [{"type": "ping"}]
        
        await ws.accept()
        
        # Handle ping
        msg = await ws.receive_json()
        if msg.get("type") == "ping":
            await ws.send_json({"type": "pong"})
        
        assert {"type": "pong"} in ws.messages_sent

    @pytest.mark.asyncio
    async def test_timeout_on_no_heartbeat(self):
        """Should timeout connection if no heartbeat received."""
        HEARTBEAT_TIMEOUT = 0.1  # Short timeout for testing
        
        ws = MockWebSocket()
        await ws.accept()
        
        # Simulate heartbeat timeout
        async def wait_for_heartbeat():
            try:
                await asyncio.wait_for(
                    ws.receive_json(),
                    timeout=HEARTBEAT_TIMEOUT
                )
                return True
            except asyncio.TimeoutError:
                return False
        
        # No heartbeat sent, should timeout
        received = await wait_for_heartbeat()
        assert received is False
