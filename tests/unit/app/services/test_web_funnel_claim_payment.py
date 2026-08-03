"""RevenueCat web-lead reconciliation never trusts a browser or an unknown ID."""

from datetime import timedelta

import pytest

from src.app.services.web_funnel_claim_payment import (
    process_claim_email,
    process_revenuecat_reconcile,
    reconcile_revenuecat_event,
)
from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelOutbox,
    WebFunnelProviderEvent,
)


class FakePaymentSession:
    def __init__(self, lead):
        self.lead = lead
        self.added = []
        self.committed = False

    async def get(self, _model, _id, **_kwargs):
        return self.lead

    async def scalar(self, _statement):
        return None

    async def scalars(self, _statement):
        class Empty:
            def all(self):
                return []
        return Empty()

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.committed = True


def _lead():
    return WebFunnelLead(id="11111111-1111-1111-1111-111111111111", email="buyer@example.com", access_key_hash="hash", request_id="request", snapshot_version="v1", snapshot={}, snapshot_hash="snapshot", status="draft", revision=1, access_sync_status="pending")


@pytest.mark.asyncio
async def test_unknown_or_non_uuid_revenuecat_id_stays_on_native_path():
    assert not await reconcile_revenuecat_event(FakePaymentSession(None), {"id": "event", "app_user_id": "$RCAnonymousID:abc"}, None)


@pytest.mark.asyncio
async def test_authoritative_standard_enqueues_one_claim_email(monkeypatch):
    from src.app.services import web_funnel_claim_payment as payment

    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_PRODUCT_IDS", "web_monthly")
    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_ENVIRONMENT", "PRODUCTION")
    session = FakePaymentSession(_lead())
    active = {"subscriber": {"entitlements": {"standard": {"expires_date": None}}}}
    handled = await reconcile_revenuecat_event(session, {"id": "event-1", "type": "INITIAL_PURCHASE", "app_user_id": session.lead.id, "product_id": "web_monthly", "environment": "PRODUCTION"}, active)
    assert handled
    assert session.lead.status == "email_queued"
    assert "claim_email" in {getattr(row, "job_type", None) for row in session.added}
    assert session.committed


class FakeReconcileSession(FakePaymentSession):
    def __init__(self, lead, event):
        super().__init__(lead)
        self.event = event
        self.scalar_calls = 0

    async def scalar(self, _statement):
        self.scalar_calls += 1
        return self.event if self.scalar_calls == 1 else None


class ActiveSubscriber:
    async def get_subscriber_info(self, _app_user_id):
        return {"subscriber": {"entitlements": {"standard": {"expires_date": None}}}}


@pytest.mark.asyncio
async def test_deferred_reconcile_uses_provider_event_id_and_queues_email(monkeypatch):
    from src.app.services import web_funnel_claim_payment as payment

    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_PRODUCT_IDS", "web_monthly")
    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_ENVIRONMENT", "PRODUCTION")
    lead = _lead()
    event = WebFunnelProviderEvent(
        id="inbox-1",
        provider_event_id="provider-event-1",
        event_type="INITIAL_PURCHASE",
        lead_id=lead.id,
        payload={"product_id": "web_monthly", "environment": "PRODUCTION"},
    )
    outbox = WebFunnelOutbox(
        id="outbox-1",
        idempotency_key="revenuecat-reconcile:provider-event-1",
        job_type="revenuecat_reconcile",
        payload={"provider_event_id": "provider-event-1", "lead_id": lead.id},
        status="pending",
        attempts=0,
        next_attempt_at=payment.utcnow(),
    )
    session = FakeReconcileSession(lead, event)
    assert await process_revenuecat_reconcile(session, outbox, ActiveSubscriber())
    assert outbox.status == "completed"
    assert lead.status == "email_queued"
    assert any(row.job_type == "claim_email" for row in session.added)


@pytest.mark.asyncio
async def test_new_claim_email_revokes_every_older_usable_generation():
    from src.app.services import web_funnel_claim_payment as payment

    old_claim = payment.WebFunnelClaim(
        id="claim-old",
        lead_id=_lead().id,
        generation=1,
        magic_token_hash="old-hash",
        expires_at=payment.utcnow() + timedelta(hours=1),
    )

    class ClaimEmailSession(FakePaymentSession):
        async def scalars(self, _statement):
            class Claims:
                def all(self):
                    return [old_claim]

            return Claims()

    outbox = WebFunnelOutbox(
        id="outbox-2",
        idempotency_key=f"claim-email:{_lead().id}:2",
        job_type="claim_email",
        payload={"lead_id": _lead().id, "generation": 2},
        status="pending",
        attempts=0,
        next_attempt_at=payment.utcnow(),
    )

    async def send(_email, _token, _lead_id):
        return True

    session = ClaimEmailSession(_lead())
    await process_claim_email(session, outbox, send)
    assert old_claim.revoked_at is not None
    assert any(
        isinstance(row, payment.WebFunnelClaim) and row.generation == 2
        for row in session.added
    )


@pytest.mark.asyncio
async def test_deferred_refund_revokes_claims_without_trusting_stale_standard(monkeypatch):
    from src.app.services import web_funnel_claim_payment as payment

    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_PRODUCT_IDS", "web_monthly")
    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_ENVIRONMENT", "PRODUCTION")
    lead = _lead()
    event = WebFunnelProviderEvent(
        id="inbox-refund",
        provider_event_id="provider-refund",
        event_type="REFUND",
        lead_id=lead.id,
        payload={"product_id": "web_monthly", "environment": "PRODUCTION"},
    )
    outbox = WebFunnelOutbox(
        id="outbox-refund",
        idempotency_key="revenuecat-reconcile:provider-refund",
        job_type="revenuecat_reconcile",
        payload={"provider_event_id": "provider-refund", "lead_id": lead.id},
        status="pending",
        attempts=0,
        next_attempt_at=payment.utcnow(),
    )

    class MustNotFetch:
        async def get_subscriber_info(self, _app_user_id):
            raise AssertionError("refund must not be fulfilled from stale entitlement")

    session = FakeReconcileSession(lead, event)
    assert await process_revenuecat_reconcile(session, outbox, MustNotFetch())
    assert lead.status == "refunded"
    assert outbox.status == "completed"


@pytest.mark.asyncio
async def test_deferred_expiration_converges_when_standard_is_no_longer_active(monkeypatch):
    from src.app.services import web_funnel_claim_payment as payment

    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_PRODUCT_IDS", "web_monthly")
    monkeypatch.setattr(payment.settings, "WEB_FUNNEL_REVENUECAT_ENVIRONMENT", "PRODUCTION")
    lead = _lead()
    event = WebFunnelProviderEvent(
        id="inbox-expiry",
        provider_event_id="provider-expiry",
        event_type="EXPIRATION",
        lead_id=lead.id,
        payload={"product_id": "web_monthly", "environment": "PRODUCTION"},
    )
    outbox = WebFunnelOutbox(
        id="outbox-expiry",
        idempotency_key="revenuecat-reconcile:provider-expiry",
        job_type="revenuecat_reconcile",
        payload={"provider_event_id": "provider-expiry", "lead_id": lead.id},
        status="pending",
        attempts=0,
        next_attempt_at=payment.utcnow(),
    )

    class InactiveSubscriber:
        async def get_subscriber_info(self, _app_user_id):
            return None

    session = FakeReconcileSession(lead, event)
    assert await process_revenuecat_reconcile(session, outbox, InactiveSubscriber())
    assert lead.status == "expired"
    assert outbox.status == "completed"
