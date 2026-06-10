"""Unit tests for affiliate outbox dispatch service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MODULE = "src.infra.services.affiliate_outbox_dispatch_service"


def _make_row(row_id="row-1", event_id="evt-1", event_type="subscription_initial_purchase"):
    row = MagicMock()
    row.id = row_id
    row.event_id = event_id
    row.event_type = event_type
    row.payload = {"mealtrack_user_id": "user-1"}
    return row


def _make_session_ctx(rows, *, mark_failed_returns=False):
    """Build nested async context manager mocks for AsyncSessionLocal()."""
    repo = MagicMock()
    repo.claim_pending = AsyncMock(return_value=rows)
    repo.mark_sent = AsyncMock()
    repo.mark_failed = AsyncMock(return_value=mark_failed_returns)

    txn_ctx = MagicMock()
    txn_ctx.__aenter__ = AsyncMock(return_value=None)
    txn_ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.begin = MagicMock(return_value=txn_ctx)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    return session, repo


@pytest.mark.asyncio
async def test_dispatch_sends_pending_rows():
    row = _make_row()
    session, repo = _make_session_ctx([row])

    with (
        patch(f"{MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{MODULE}.AffiliateEventOutboxRepository", return_value=repo),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_adapter_cls,
    ):
        mock_adapter_cls.return_value.send_event = AsyncMock(return_value=True)
        from src.infra.services.affiliate_outbox_dispatch_service import (
            dispatch_affiliate_outbox,
        )
        summary = await dispatch_affiliate_outbox()

    assert summary["sent"] == 1
    assert summary["failed"] == 0
    mock_adapter_cls.return_value.send_event.assert_awaited_once()
    sent_payload = mock_adapter_cls.return_value.send_event.call_args[0][0]
    assert sent_payload["event_id"] == "evt-1"
    assert sent_payload["event_type"] == "subscription_initial_purchase"
    assert sent_payload["mealtrack_user_id"] == "user-1"


@pytest.mark.asyncio
async def test_dispatch_marks_failed_when_send_returns_false():
    row = _make_row()
    session, repo = _make_session_ctx([row])

    with (
        patch(f"{MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{MODULE}.AffiliateEventOutboxRepository", return_value=repo),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_adapter_cls,
    ):
        mock_adapter_cls.return_value.send_event = AsyncMock(return_value=False)
        from src.infra.services.affiliate_outbox_dispatch_service import (
            dispatch_affiliate_outbox,
        )
        summary = await dispatch_affiliate_outbox()

    assert summary["sent"] == 0
    assert summary["failed"] == 1


@pytest.mark.asyncio
async def test_dispatch_marks_failed_on_exception():
    row = _make_row()
    session, repo = _make_session_ctx([row])

    with (
        patch(f"{MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{MODULE}.AffiliateEventOutboxRepository", return_value=repo),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_adapter_cls,
    ):
        mock_adapter_cls.return_value.send_event = AsyncMock(
            side_effect=Exception("connection error")
        )
        from src.infra.services.affiliate_outbox_dispatch_service import (
            dispatch_affiliate_outbox,
        )
        summary = await dispatch_affiliate_outbox()

    assert summary["sent"] == 0
    assert summary["failed"] == 1


@pytest.mark.asyncio
async def test_dispatch_no_rows_returns_zero_counts():
    session, repo = _make_session_ctx([])

    with (
        patch(f"{MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{MODULE}.AffiliateEventOutboxRepository", return_value=repo),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_adapter_cls,
    ):
        from src.infra.services.affiliate_outbox_dispatch_service import (
            dispatch_affiliate_outbox,
        )
        summary = await dispatch_affiliate_outbox()

    assert summary == {"sent": 0, "failed": 0, "permanently_failed": 0, "skipped": 0}
    mock_adapter_cls.return_value.send_event.assert_not_called()


@pytest.mark.asyncio
async def test_permanently_failed_row_triggers_sentry_alert():
    """Row that exhausts all retries captures a Sentry error."""
    row = _make_row()
    session, repo = _make_session_ctx([row], mark_failed_returns=True)

    with (
        patch(f"{MODULE}.AsyncSessionLocal", return_value=session),
        patch(f"{MODULE}.AffiliateEventOutboxRepository", return_value=repo),
        patch(f"{MODULE}.AffiliateServiceAdapter") as mock_adapter_cls,
        patch(f"{MODULE}.sentry_sdk") as mock_sentry,
    ):
        mock_adapter_cls.return_value.send_event = AsyncMock(return_value=False)
        from src.infra.services.affiliate_outbox_dispatch_service import (
            dispatch_affiliate_outbox,
        )
        summary = await dispatch_affiliate_outbox()

    assert summary["permanently_failed"] == 1
    mock_sentry.capture_message.assert_called_once()
    msg = mock_sentry.capture_message.call_args[0][0]
    assert "permanently failed" in msg
    assert "row-1" in msg
