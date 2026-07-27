"""Tests for backend-owned web funnel checkout service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.app.services.web_funnel_checkout_service import WebFunnelCheckoutService
from src.domain.ports.paypal_billing_port import PayPalSubscriptionSnapshot
from src.infra.database.models.web_funnel import WebFunnelLead


class FakeWebFunnelRepo:
    def __init__(self):
        self.lead = WebFunnelLead(id="lead-row", external_lead_id="lead-1")
        self.by_idempotency = {}
        self.by_id = {}
        self.by_claim_hash = {}
        self.verified_payment_event = None
        self.marked_paid = False

    async def get_or_create_lead(self, external_lead_id, billing_country):
        self.lead.external_lead_id = external_lead_id
        self.lead.last_seen_country = billing_country
        return self.lead

    async def find_by_lead_idempotency(self, lead_id, idempotency_key_hash):
        return self.by_idempotency.get((lead_id, idempotency_key_hash))

    async def add_checkout(self, checkout):
        checkout.id = "checkout-1"
        self.by_id[checkout.id] = checkout
        self.by_idempotency[
            (checkout.lead_id, checkout.idempotency_key_hash)
        ] = checkout
        return checkout

    async def find_by_id(self, checkout_id):
        return self.by_id.get(checkout_id)

    async def record_confirmation(self, checkout, subscription_id):
        checkout.provider_subscription_id = subscription_id
        checkout.state = "pending_payment"
        return checkout

    async def find_latest_verified_event_for_subscription(
        self, provider, provider_subscription_id, event_types
    ):
        if self.verified_payment_event and provider_subscription_id == "I-SUB":
            return self.verified_payment_event
        return None

    async def mark_paid(self, checkout):
        self.marked_paid = True
        checkout.state = "paid_active"
        return checkout

    async def find_by_claim_hash(self, claim_token_hash):
        return self.by_claim_hash.get(claim_token_hash)

    async def claim_checkout(self, checkout, user_id):
        checkout.claimed_at = object()
        checkout.state = "claimed"
        return SimpleNamespace(id="sub-1", user_id=user_id)


class FakeUow:
    def __init__(self):
        self.web_funnel_checkouts = FakeWebFunnelRepo()
        self.session = SimpleNamespace(flush=AsyncMock())


class FakePayPal:
    def __init__(self, *, plan_id, custom_id):
        self.plan_id = plan_id
        self.custom_id = custom_id

    async def get_subscription(self, subscription_id):
        return PayPalSubscriptionSnapshot(
            id=subscription_id,
            plan_id=self.plan_id,
            custom_id=self.custom_id,
            status="APPROVAL_PENDING",
        )


def _settings(enabled=True):
    return SimpleNamespace(
        WEB_FUNNEL_SIGNING_SECRET="test-secret",
        WEB_FUNNEL_CHECKOUT_ENABLED=enabled,
        WEB_FUNNEL_CLAIM_TOKEN_TTL_MINUTES=60,
        web_funnel_paypal_offers={
            "premium_monthly": {
                "reward_id": "WELCOME50",
                "provider": "paypal",
                "currency": "USD",
                "amount_minor": 499,
                "renewal_interval": "monthly",
                "paypal_plan_id": "P-PLAN",
                "welcome_discount_percent": 50,
            }
        },
    )


@pytest.mark.asyncio
async def test_create_checkout_is_idempotent_for_same_payload():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()

    checkout, custom_id = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )
    repeated, repeated_custom_id = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )

    assert repeated is checkout
    assert repeated_custom_id == custom_id
    assert checkout.provider_plan_id == "P-PLAN"
    assert checkout.currency == "USD"
    assert checkout.welcome_discount_percent == 50


@pytest.mark.asyncio
async def test_create_checkout_rejects_idempotency_conflict():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()
    await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_checkout(
            uow=uow,
            lead_id="lead-1",
            offer_id="premium_monthly",
            reward_id="WELCOME50",
            billing_country="CA",
            idempotency_key="idem-key-1",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_vietnam_checkout_fails_closed_without_momo():
    service = WebFunnelCheckoutService(_settings())

    with pytest.raises(HTTPException) as exc:
        await service.create_checkout(
            uow=FakeUow(),
            lead_id="lead-1",
            offer_id="premium_monthly",
            reward_id="WELCOME50",
            billing_country="VN",
            idempotency_key="idem-key-1",
        )

    assert exc.value.status_code == 503
    assert exc.value.detail["error_code"] == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_paypal_confirmation_binds_reference_without_granting_access():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()
    checkout, custom_id = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )

    confirmed = await service.confirm_paypal_subscription(
        uow=uow,
        paypal=FakePayPal(plan_id="P-PLAN", custom_id=custom_id),
        checkout_id=checkout.id,
        subscription_id="I-SUB",
    )

    assert confirmed.provider_subscription_id == "I-SUB"
    assert confirmed.state == "pending_payment"


@pytest.mark.asyncio
async def test_paypal_confirmation_rejects_plan_mismatch():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()
    checkout, custom_id = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )

    with pytest.raises(HTTPException) as exc:
        await service.confirm_paypal_subscription(
            uow=uow,
            paypal=FakePayPal(plan_id="P-OTHER", custom_id=custom_id),
            checkout_id=checkout.id,
            subscription_id="I-SUB",
        )

    assert exc.value.detail["error_code"] == "PLAN_MISMATCH"


@pytest.mark.asyncio
async def test_paypal_confirmation_rejects_malformed_custom_id():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()
    checkout, _ = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )

    with pytest.raises(HTTPException) as exc:
        await service.confirm_paypal_subscription(
            uow=uow,
            paypal=FakePayPal(plan_id="P-PLAN", custom_id="not-json.bad-signature"),
            checkout_id=checkout.id,
            subscription_id="I-SUB",
        )

    assert exc.value.detail["error_code"] == "INVALID_CUSTOM_ID"


@pytest.mark.asyncio
async def test_paypal_confirmation_reconciles_early_verified_payment_event():
    service = WebFunnelCheckoutService(_settings())
    uow = FakeUow()
    checkout, custom_id = await service.create_checkout(
        uow=uow,
        lead_id="lead-1",
        offer_id="premium_monthly",
        reward_id="WELCOME50",
        billing_country="US",
        idempotency_key="idem-key-1",
    )
    uow.web_funnel_checkouts.verified_payment_event = object()

    confirmed = await service.confirm_paypal_subscription(
        uow=uow,
        paypal=FakePayPal(plan_id="P-PLAN", custom_id=custom_id),
        checkout_id=checkout.id,
        subscription_id="I-SUB",
    )

    assert confirmed.state == "pending_payment"

    active_snapshot = PayPalSubscriptionSnapshot(
        id="I-SUB",
        plan_id="P-PLAN",
        custom_id=custom_id,
        status="ACTIVE",
    )
    await service._apply_early_verified_payment_if_present(
        uow=uow, checkout=confirmed, snapshot=active_snapshot
    )

    assert uow.web_funnel_checkouts.marked_paid is True
    assert confirmed.state == "paid_active"
