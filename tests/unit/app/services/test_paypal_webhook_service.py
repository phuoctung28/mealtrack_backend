"""Tests for verified PayPal webhook state transitions."""

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

from src.app.services.paypal_webhook_service import PayPalWebhookService
from src.domain.ports.paypal_billing_port import (
    PayPalSubscriptionSnapshot,
    PayPalWebhookVerification,
)
from src.infra.adapters.paypal_billing_adapter import PayPalBillingAdapter


def _signed_custom_id(checkout_id: str, secret: str = "secret") -> str:
    payload = json.dumps(
        {"checkout_id": checkout_id, "provider": "paypal"},
        separators=(",", ":"),
        sort_keys=True,
    )
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


class FakeWebFunnelRepo:
    def __init__(self, checkout):
        self.checkout = checkout
        self.events = set()
        self.marked_paid = False
        self.revoked_reason = None
        self.subscription = SimpleNamespace(status="active")
        self.recorded_checkout_id = None

    async def find_by_provider_subscription(self, provider, provider_subscription_id):
        if (
            provider == "paypal"
            and provider_subscription_id == self.checkout.provider_subscription_id
        ):
            return self.checkout
        return None

    async def record_provider_event(
        self,
        provider,
        event_id,
        event_type,
        provider_subscription_id,
        checkout_id,
        verified,
        processing_result,
    ):
        if event_id in self.events:
            return SimpleNamespace(id="event-1"), False
        self.events.add(event_id)
        self.recorded_checkout_id = checkout_id
        return SimpleNamespace(id="event-1"), True

    async def mark_paid(self, checkout):
        self.marked_paid = True
        checkout.state = "paid_active"
        return checkout

    async def mark_revoked(self, checkout, reason):
        self.revoked_reason = reason
        checkout.state = "revoked"
        self.subscription.status = "refunded" if "refund" in reason else "cancelled"
        return checkout


class FakeUow:
    def __init__(self, checkout):
        self.web_funnel_checkouts = FakeWebFunnelRepo(checkout)


class FakePayPal:
    def __init__(self, *, event_type, snapshot):
        self.event_type = event_type
        self.snapshot = snapshot

    async def verify_webhook(self, headers, raw_body):
        return PayPalWebhookVerification(
            verified=True,
            event_id="evt-1",
            event_type=self.event_type,
            resource_id="I-SUB",
        )

    async def get_subscription(self, subscription_id):
        return self.snapshot


def _checkout():
    return SimpleNamespace(
        id="checkout-1",
        provider="paypal",
        provider_subscription_id="I-SUB",
        provider_plan_id="P-PLAN",
        currency="USD",
        amount_minor=999,
        state="pending_payment",
    )


def _snapshot(**overrides):
    values = {
        "id": "I-SUB",
        "plan_id": "P-PLAN",
        "custom_id": _signed_custom_id("checkout-1"),
        "status": "ACTIVE",
        "merchant_id": "merchant-1",
        "currency": "USD",
        "amount_minor": 999,
    }
    values.update(overrides)
    return PayPalSubscriptionSnapshot(**values)


def test_paypal_snapshot_uses_exact_decimal_minor_units():
    snapshot = PayPalBillingAdapter._subscription_snapshot(
        {
            "id": "I-SUB",
            "plan_id": "P-PLAN",
            "custom_id": _signed_custom_id("checkout-1"),
            "status": "ACTIVE",
            "billing_info": {
                "last_payment": {
                    "amount": {"value": "10.00", "currency_code": "USD"}
                }
            },
        }
    )

    assert snapshot.amount_minor == 1000


def test_paypal_snapshot_rejects_overprecise_amount():
    with pytest.raises(ValueError):
        PayPalBillingAdapter._subscription_snapshot(
            {
                "id": "I-SUB",
                "billing_info": {
                    "last_payment": {
                        "amount": {"value": "10.015", "currency_code": "USD"}
                    }
                },
            }
        )


def test_paypal_sale_webhook_prefers_billing_agreement_id():
    subscription_id = PayPalBillingAdapter._webhook_subscription_id(
        "PAYMENT.SALE.COMPLETED",
        {"id": "PAYMENT-ID", "billing_agreement_id": "I-SUB"},
    )

    assert subscription_id == "I-SUB"


@pytest.mark.asyncio
async def test_completed_payment_with_full_snapshot_match_marks_paid():
    checkout = _checkout()
    uow = FakeUow(checkout)
    service = PayPalWebhookService(
        expected_merchant_id="merchant-1", signing_secret="secret"
    )

    result = await service.process(
        uow=uow,
        paypal=FakePayPal(
            event_type="PAYMENT.CAPTURE.COMPLETED", snapshot=_snapshot()
        ),
        headers={},
        raw_body=b"{}",
    )

    assert result["state"] == "paid_active"
    assert uow.web_funnel_checkouts.marked_paid is True


@pytest.mark.asyncio
async def test_subscription_activation_alone_does_not_mark_paid():
    checkout = _checkout()
    uow = FakeUow(checkout)
    service = PayPalWebhookService(
        expected_merchant_id="merchant-1", signing_secret="secret"
    )

    result = await service.process(
        uow=uow,
        paypal=FakePayPal(
            event_type="BILLING.SUBSCRIPTION.ACTIVATED", snapshot=_snapshot()
        ),
        headers={},
        raw_body=b"{}",
    )

    assert result["reason"] == "non_entitling_event"
    assert uow.web_funnel_checkouts.marked_paid is False


@pytest.mark.asyncio
async def test_amount_mismatch_does_not_mark_paid():
    checkout = _checkout()
    uow = FakeUow(checkout)
    service = PayPalWebhookService(
        expected_merchant_id="merchant-1", signing_secret="secret"
    )

    result = await service.process(
        uow=uow,
        paypal=FakePayPal(
            event_type="PAYMENT.CAPTURE.COMPLETED",
            snapshot=_snapshot(amount_minor=100),
        ),
        headers={},
        raw_body=b"{}",
    )

    assert result["reason"] == "amount_mismatch"
    assert uow.web_funnel_checkouts.marked_paid is False


@pytest.mark.asyncio
async def test_refund_revokes_checkout_and_subscription():
    checkout = _checkout()
    uow = FakeUow(checkout)
    service = PayPalWebhookService(
        expected_merchant_id="merchant-1", signing_secret="secret"
    )

    result = await service.process(
        uow=uow,
        paypal=FakePayPal(event_type="PAYMENT.SALE.REFUNDED", snapshot=_snapshot()),
        headers={},
        raw_body=b"{}",
    )

    assert result["state"] == "revoked"
    assert uow.web_funnel_checkouts.subscription.status == "refunded"


@pytest.mark.asyncio
async def test_verified_webhook_before_confirmation_is_stored_for_reconciliation():
    checkout = _checkout()
    checkout.provider_subscription_id = None
    uow = FakeUow(checkout)
    service = PayPalWebhookService(
        expected_merchant_id="merchant-1", signing_secret="secret"
    )

    result = await service.process(
        uow=uow,
        paypal=FakePayPal(
            event_type="PAYMENT.CAPTURE.COMPLETED", snapshot=_snapshot()
        ),
        headers={},
        raw_body=b"{}",
    )

    assert result == {"status": "stored", "reason": "checkout_not_found"}
    assert uow.web_funnel_checkouts.recorded_checkout_id is None
