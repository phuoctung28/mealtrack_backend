"""Claim handoff links and independent outbox recovery guards."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from src.app.services.web_funnel_claim_common import utcnow
from src.infra.database.models.web_funnel_claim import WebFunnelOutbox
from src.infra.services import web_funnel_outbox_dispatch_service as dispatcher


def test_claim_link_keeps_magic_credential_out_of_http_request(monkeypatch):
    monkeypatch.setattr(
        dispatcher.settings,
        "WEB_FUNNEL_CLAIM_LINK_BASE_URL",
        "https://nutree.app/open-nutree",
    )

    url = dispatcher.claim_link("lead-1", "opaque-token")

    assert url == (
        "https://nutree.app/open-nutree#v=2&lead_id=lead-1&magic_token=opaque-token"
    )
    assert "?" not in url


class _Session:
    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def scalars(self, _statement):
        class _Rows:
            def __init__(self, rows):
                self.rows = rows

            def all(self):
                return self.rows

        return _Rows(self.rows)


def _outbox(job_type: str) -> WebFunnelOutbox:
    return WebFunnelOutbox(
        id="outbox-1",
        idempotency_key=f"{job_type}:1",
        job_type=job_type,
        payload={"lead_id": "lead-1", "provider_event_id": "event-1"},
        status="pending",
        attempts=0,
        next_attempt_at=utcnow() - timedelta(seconds=1),
    )


@pytest.mark.asyncio
async def test_reconcile_worker_runs_alongside_claim_email_delivery(monkeypatch):
    reconcile = AsyncMock(return_value=True)
    monkeypatch.setattr(
        dispatcher,
        "AsyncSessionLocal",
        lambda: _Session([_outbox("revenuecat_reconcile")]),
    )
    monkeypatch.setattr(dispatcher, "process_revenuecat_reconcile", reconcile)

    assert await dispatcher.dispatch_web_funnel_outbox() == 1
    assert reconcile.await_count == 1


@pytest.mark.asyncio
async def test_claim_email_stays_queued_without_claim_link_base_url(monkeypatch):
    send = AsyncMock()
    monkeypatch.setattr(dispatcher.settings, "WEB_FUNNEL_CLAIM_LINK_BASE_URL", "")
    monkeypatch.setattr(
        dispatcher, "AsyncSessionLocal", lambda: _Session([_outbox("claim_email")])
    )
    monkeypatch.setattr(dispatcher, "process_claim_email", send)

    assert await dispatcher.dispatch_web_funnel_outbox() == 0
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_email_stays_queued_when_legacy_claims_are_disabled(monkeypatch):
    send = AsyncMock()
    monkeypatch.setattr(
        dispatcher.settings,
        "WEB_FUNNEL_CLAIM_LINK_BASE_URL",
        "https://nutree.app/open-nutree",
    )
    monkeypatch.setattr(dispatcher.settings, "WEB_FUNNEL_LEGACY_CLAIM_ENABLED", False)
    monkeypatch.setattr(
        dispatcher, "AsyncSessionLocal", lambda: _Session([_outbox("claim_email")])
    )
    monkeypatch.setattr(dispatcher, "process_claim_email", send)

    assert await dispatcher.dispatch_web_funnel_outbox() == 0
    send.assert_not_awaited()
