from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.ports.outbox_handler_port import OutboxEventContext
from src.infra.services.handlers.firebase_account_cleanup_handler import (
    FirebaseAccountCleanupHandler,
)
from src.infra.services.handlers.notification_reschedule_handler import (
    NotificationRescheduleHandler,
)


def _context(event_type: str) -> OutboxEventContext:
    return OutboxEventContext(
        outbox_id="out-1",
        event_id="event-1",
        event_type=event_type,
        retry_count=0,
        created_at_iso="2026-08-22T00:00:00Z",
    )


class TestFirebaseAccountCleanupHandler:
    @pytest.mark.asyncio
    async def test_invalid_payload_is_permanent(self):
        handler = FirebaseAccountCleanupHandler(MagicMock())

        result = await handler.handle({}, _context("firebase_account_cleanup"))

        assert result.success is False
        assert result.is_transient is False
        assert result.error_type == "InvalidPayload"

    @pytest.mark.asyncio
    async def test_revoke_and_delete_success(self):
        service = MagicMock()
        service.revoke_refresh_tokens.return_value = True
        service.delete_firebase_user.return_value = True

        result = await FirebaseAccountCleanupHandler(service).handle(
            {"firebase_uid": "firebase-1"}, _context("firebase_account_cleanup")
        )

        assert result.success is True
        service.revoke_refresh_tokens.assert_called_once_with("firebase-1")
        service.delete_firebase_user.assert_called_once_with("firebase-1")

    @pytest.mark.asyncio
    async def test_revoke_failure_is_transient(self):
        service = MagicMock()
        service.revoke_refresh_tokens.return_value = False

        result = await FirebaseAccountCleanupHandler(service).handle(
            {"firebase_uid": "firebase-1"}, _context("firebase_account_cleanup")
        )

        assert result.success is False
        assert result.is_transient is True
        assert result.error_type == "FirebaseTokenRevocationError"
        service.delete_firebase_user.assert_not_called()


class TestNotificationRescheduleHandler:
    @pytest.mark.asyncio
    async def test_invalid_payload_is_permanent(self):
        handler = NotificationRescheduleHandler(MagicMock())

        result = await handler.handle({}, _context("notification_reschedule"))

        assert result.success is False
        assert result.is_transient is False
        assert result.error_type == "InvalidPayload"

    @pytest.mark.asyncio
    async def test_reschedules_user_notifications(self):
        service = MagicMock()
        service.reschedule_user_notifications = AsyncMock(return_value=4)

        result = await NotificationRescheduleHandler(service).handle(
            {"user_id": "u1"}, _context("notification_reschedule")
        )

        assert result.success is True
        assert result.metadata["scheduled_count"] == 4
        service.reschedule_user_notifications.assert_awaited_once_with("u1")

    @pytest.mark.asyncio
    async def test_reschedule_failure_is_transient(self):
        service = MagicMock()
        service.reschedule_user_notifications = AsyncMock(
            side_effect=RuntimeError("database unavailable")
        )

        result = await NotificationRescheduleHandler(service).handle(
            {"user_id": "u1"}, _context("notification_reschedule")
        )

        assert result.success is False
        assert result.is_transient is True
        assert result.error_type == "RuntimeError"
