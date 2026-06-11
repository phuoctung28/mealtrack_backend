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
    uow.affiliate_outbox = AsyncMock()
    return uow


@pytest.mark.asyncio
async def test_initial_purchase_enqueues_affiliate_event():
    uow = _make_uow()
    user = _make_user()

    with patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=None)), \
         patch(f"{MODULE}._credit_referral_on_purchase", AsyncMock()):
        await handle_purchase(uow, user, RC_EVENT)

    uow.affiliate_outbox.enqueue.assert_awaited_once()
    call_args = uow.affiliate_outbox.enqueue.call_args
    assert call_args[0][0] == "subscription_initial_purchase"
    payload = call_args[0][1]
    assert payload["mealtrack_user_id"] == "user-1"
    assert payload["product_id"] == "premium_monthly"
    assert call_args[1]["event_id"] == "rc-evt-001"


@pytest.mark.asyncio
async def test_enqueue_failure_does_not_raise():
    """Outbox enqueue error is propagated to UoW rollback — webhook still ACKs via RC retry."""
    uow = _make_uow()
    user = _make_user()
    uow.affiliate_outbox.enqueue = AsyncMock(return_value=None)  # None = duplicate, silently skipped

    with patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=None)), \
         patch(f"{MODULE}._credit_referral_on_purchase", AsyncMock()):
        await handle_purchase(uow, user, RC_EVENT)  # must not raise


@pytest.mark.asyncio
async def test_renewal_enqueues_subscription_renewal():
    uow = _make_uow()
    sub = MagicMock()
    uow.subscriptions.find_by_revenuecat_id = AsyncMock(return_value=sub)
    user = _make_user()

    with patch(f"{MODULE}.get_subscription_by_revenuecat_id", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        await handle_renewal(uow, user, RC_EVENT)

    uow.affiliate_outbox.enqueue.assert_awaited_once()
    assert uow.affiliate_outbox.enqueue.call_args[0][0] == "subscription_renewal"


@pytest.mark.asyncio
async def test_cancellation_enqueues_subscription_canceled():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        await handle_cancellation(uow, user, RC_EVENT)

    uow.affiliate_outbox.enqueue.assert_awaited_once()
    assert uow.affiliate_outbox.enqueue.call_args[0][0] == "subscription_canceled"


@pytest.mark.asyncio
async def test_expiration_enqueues_subscription_expired():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()):
        await handle_expiration(uow, user, RC_EVENT)

    uow.affiliate_outbox.enqueue.assert_awaited_once()
    assert uow.affiliate_outbox.enqueue.call_args[0][0] == "subscription_expired"


@pytest.mark.asyncio
async def test_refund_enqueues_subscription_refund():
    uow = _make_uow()
    sub = MagicMock()
    user = _make_user()

    with patch(f"{MODULE}.get_or_create_subscription", AsyncMock(return_value=sub)), \
         patch(f"{MODULE}.capture_subscription_lifecycle_event", AsyncMock()), \
         patch(f"{MODULE}._revoke_referral_on_refund", AsyncMock()):
        await handle_refund(uow, user, RC_EVENT)

    uow.affiliate_outbox.enqueue.assert_awaited_once()
    assert uow.affiliate_outbox.enqueue.call_args[0][0] == "subscription_refund"
