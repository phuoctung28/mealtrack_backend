"""Focused safety tests for opaque RevenueCat redemption-link preflight."""

import pytest

from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)
from src.infra.services.web_funnel_redemption_service import WebFunnelRedemptionService


class Session:
    def __init__(self, binding, lead):
        self.binding = binding
        self.lead = lead
        self.committed = False

    async def scalar(self, _statement):
        return self.binding

    async def get(self, _model, _identifier, **_kwargs):
        return self.lead

    async def commit(self):
        self.committed = True


def _lead(email="buyer@example.com"):
    return WebFunnelLead(id="lead-1", email=email)


def _binding(**values):
    return WebFunnelRedemption(lead_id="lead-1", **values)


@pytest.mark.asyncio
async def test_preflight_binds_matching_verified_identity():
    binding = _binding()
    session = Session(binding, _lead())

    assert await WebFunnelRedemptionService().preflight(
        session,
        uid="firebase-uid",
        email="buyer@example.com",
        redemption_url="rc-example://redeem?token=opaque",
    )
    assert binding.preflight_uid == "firebase-uid"
    assert binding.preflight_at is not None
    assert session.committed


@pytest.mark.asyncio
async def test_preflight_rejects_unknown_link_or_checkout_email_mismatch():
    service = WebFunnelRedemptionService()

    assert not await service.preflight(
        Session(None, _lead()),
        uid="firebase-uid",
        email="buyer@example.com",
        redemption_url="rc-example://unknown",
    )
    assert not await service.preflight(
        Session(_binding(), _lead()),
        uid="firebase-uid",
        email="other@example.com",
        redemption_url="rc-example://redeem?token=opaque",
    )


@pytest.mark.asyncio
async def test_preflight_rejects_replayed_redemption_binding():
    assert not await WebFunnelRedemptionService().preflight(
        Session(_binding(redeemer_uid="firebase-uid"), _lead()),
        uid="firebase-uid",
        email="buyer@example.com",
        redemption_url="rc-example://redeem?token=opaque",
    )
