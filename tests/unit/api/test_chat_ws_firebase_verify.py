"""Cover verify_firebase_token_and_get_user_id in chat_ws."""
import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.exceptions import WebSocketException

from src.api.routes.v1 import chat_ws


def test_verify_success_returns_db_user_id(monkeypatch):
    user = MagicMock()
    user.id = "db-uuid"

    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = user

    def fake_get_db():
        yield session

    decoded = {"uid": "firebase-abc"}
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        lambda token: decoded,
    )
    monkeypatch.setattr(chat_ws, "get_db", fake_get_db)

    uid = asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("token"))
    assert uid == "db-uuid"
    session.close.assert_called_once()


def test_verify_raises_when_uid_missing(monkeypatch):
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        lambda token: {},
    )

    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_verify_raises_when_user_not_found(monkeypatch):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None

    def fake_get_db():
        yield session

    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        lambda token: {"uid": "fb"},
    )
    monkeypatch.setattr(chat_ws, "get_db", fake_get_db)

    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_verify_expired_token(monkeypatch):
    err = chat_ws.firebase_auth.ExpiredIdTokenError("expired", None)
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        MagicMock(side_effect=err),
    )
    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_verify_revoked_token(monkeypatch):
    err = chat_ws.firebase_auth.RevokedIdTokenError("revoked")
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        MagicMock(side_effect=err),
    )
    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_verify_invalid_token(monkeypatch):
    err = chat_ws.firebase_auth.InvalidIdTokenError("bad")
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        MagicMock(side_effect=err),
    )
    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_verify_generic_error_wraps_1011(monkeypatch):
    monkeypatch.setattr(
        chat_ws.firebase_auth,
        "verify_id_token",
        MagicMock(side_effect=OSError("network")),
    )
    with pytest.raises(WebSocketException) as exc:
        asyncio.run(chat_ws.verify_firebase_token_and_get_user_id("t"))
    assert exc.value.code == status.WS_1011_INTERNAL_ERROR
