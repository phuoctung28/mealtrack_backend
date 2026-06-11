"""Unit tests for affiliate lifecycle event dispatch in RevenueCat webhook handlers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.v1.webhooks import (
    handle_cancellation,
    handle_expiration,
    handle_purchase,
    handle_refund,
    handle_renewal,
)

MODULE = "src.api.routes.v1.webhooks"

RC_EVENT = {
    "id": "rc-evt-001",
    "app_user_id": "rc-user-1",
    "product_id": "premium_monthly",
    "period_type": "NORMAL",
    "transaction_id": "txn-1",
    "expiration_at_ms": 9999999999000,
    "purchased_at_ms": 1700000000000,
    "store": "APP_STORE",
    "environment": "PRODUCTION",
}


def _make_user(uid="user-1"):
    u = MagicMock()
    u.id = uid
    u.email_opt_out = True
    return u


def _make_uow():
    uow = MagicMock()
    uow.session = MagicMock()
    uow.session.add = MagicMock()
    uow.session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        )
    )
    uow.subscriptions = MagicMock()
    uow.subscriptions.find_by_revenuecat_id = AsyncMock(return_value=None)
    uow.referrals = MagicMock()
    uow.referrals.get_conversion_by_referred_user = AsyncMock(return_value=None)
    return uow


@pytest.mark.asyncio
async def test_initial_purchase_enqueues_when_integration_enabled():
    uow = _make_uow()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=None)), \
         patch(f"{MODULE}._credit_referral_on_purchase", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_purchase(uow, user, RC_EVENT)

    mock_send.assert_awaited_once()
    payload = mock_send.call_args[0][0]
    assert payload["event_type"] == "subscription_initial_purchase"
    assert payload["mealtrack_user_id"] == "user-1"
    assert payload["event_id"] == "rc-evt-001"


@pytest.mark.asyncio
async def test_initial_purchase_skips_enqueue_when_disabled():
    uow = _make_uow()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "false"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=None)), \
         patch(f"{MODULE}._credit_referral_on_purchase", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_purchase(uow, user, RC_EVENT)

    mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_enqueue_failure_does_not_raise():
    """Affiliate send error is swallowed — webhook ACK must not fail."""
    uow = _make_uow()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=None)), \
         patch(f"{MODULE}._credit_referral_on_purchase", AsyncMock()):
        MockAdapter.return_value.send_event = AsyncMock(side_effect=Exception("HTTP down"))
        await handle_purchase(uow, user, RC_EVENT)  # must not raise


@pytest.mark.asyncio
async def test_renewal_enqueues_subscription_renewal():
    uow = _make_uow()
    sub = MagicMock()
    uow.subscriptions.find_by_revenuecat_id = AsyncMock(return_value=sub)
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_renewal(uow, user, RC_EVENT)

    mock_send.assert_awaited_once()
    assert mock_send.call_args[0][0]["event_type"] == "subscription_renewal"


@pytest.mark.asyncio
async def test_cancellation_enqueues_subscription_canceled():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_cancellation(uow, user, RC_EVENT)

    mock_send.assert_awaited_once()
    assert mock_send.call_args[0][0]["event_type"] == "subscription_canceled"


@pytest.mark.asyncio
async def test_expiration_enqueues_subscription_expired():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_expiration(uow, user, RC_EVENT)

    mock_send.assert_awaited_once()
    assert mock_send.call_args[0][0]["event_type"] == "subscription_expired"


@pytest.mark.asyncio
async def test_refund_enqueues_subscription_refund():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch.dict("os.environ", {"AFFILIATE_INTEGRATION_ENABLED": "true"}), \
         patch(f"{MODULE}.AffiliateServiceAdapter") as MockAdapter, \
         patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()), \
         patch(f"{MODULE}._revoke_referral_on_refund", AsyncMock()):
        mock_send = AsyncMock(return_value=True)
        MockAdapter.return_value.send_event = mock_send
        await handle_refund(uow, user, RC_EVENT)

    mock_send.assert_awaited_once()
    assert mock_send.call_args[0][0]["event_type"] == "subscription_refund"
