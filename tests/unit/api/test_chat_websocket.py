"""
Unit tests for chat WebSocket endpoint (auth + message loop) with mocks.
"""
import json
import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.routes.v1 import chat_ws


@pytest.fixture
def app(monkeypatch):
    """Minimal app with chat router only."""
    application = FastAPI()
    application.include_router(chat_ws.router)

    async def fake_verify(_token: str) -> str:
        return "db-user-1"

    monkeypatch.setattr(
        chat_ws,
        "verify_firebase_token_and_get_user_id",
        fake_verify,
    )

    class _Bus:
        async def send(self, msg):
            return {"thread_id": getattr(msg, "thread_id", None)}

    application.dependency_overrides[get_configured_event_bus] = lambda: _Bus()

    async def _accept_only(websocket, thread_id, user_id):
        await websocket.accept()

    monkeypatch.setattr(
        chat_ws.chat_connection_manager,
        "connect",
        _accept_only,
    )
    monkeypatch.setattr(
        chat_ws.chat_connection_manager,
        "disconnect",
        AsyncMock(),
    )

    return application


def test_chat_websocket_ping_pong_and_connected(app):
    with TestClient(app) as client:
        with client.websocket_connect("/v1/chat/ws/thread-1?token=fake") as ws:
            first = ws.receive_json()
            assert first["type"] == "connected"
            assert first["thread_id"] == "thread-1"

            ws.send_text(json.dumps({"type": "ping"}))
            pong = ws.receive_json()
            assert pong == {"type": "pong"}


def test_chat_websocket_invalid_json_sends_error(app):
    with TestClient(app) as client:
        with client.websocket_connect("/v1/chat/ws/thread-1?token=fake") as ws:
            ws.receive_json()  # connected

            ws.send_text("not-json")
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "Invalid JSON" in err["message"]


def test_chat_websocket_typing_broadcasts(app, monkeypatch):
    calls = []

    async def capture_broadcast(thread_id, is_typing):
        calls.append((thread_id, is_typing))

    monkeypatch.setattr(
        chat_ws.chat_connection_manager,
        "broadcast_typing_indicator",
        capture_broadcast,
    )
    with TestClient(app) as client:
        with client.websocket_connect("/v1/chat/ws/thread-1?token=fake") as ws:
            ws.receive_json()

            ws.send_text(json.dumps({"type": "typing", "is_typing": True}))
    assert calls == [("thread-1", True)]


def test_verify_thread_access_false_on_exception():
    class _Bus:
        async def send(self, msg):
            raise chat_ws.ResourceNotFoundException("nope")

    ok = asyncio.run(chat_ws.verify_thread_access("t1", "u1", _Bus()))
    assert ok is False


def test_verify_thread_access_true_when_send_succeeds():
    class _Bus:
        async def send(self, msg):
            return {}

    ok = asyncio.run(chat_ws.verify_thread_access("t1", "u1", _Bus()))
    assert ok is True
