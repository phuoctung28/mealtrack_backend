"""Focused safety tests for opaque RevenueCat redemption-link preflight."""

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)
from src.infra.services.web_funnel_redemption_completion import finalize_redemption
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


class StatementCaptureSession:
    statement = None

    async def scalar(self, statement):
        self.statement = statement
        return None


class FinalizationSession:
    def __init__(self, binding, lead, user, email_owner, owner_profile=None):
        self.binding = binding
        self.lead = lead
        self.scalar_results = iter([binding, user, email_owner, owner_profile])

    async def scalar(self, _statement):
        return next(self.scalar_results)

    async def get(self, _model, _identifier, **_kwargs):
        return self.lead


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


@pytest.mark.asyncio
async def test_webhook_records_provider_aliases_without_binding_firebase_identity():
    binding = _binding(original_app_user_id="$RCAnonymousID:web")
    session = Session(binding, _lead())

    assert await WebFunnelRedemptionService().record_webhook_redemption(
        session,
        {
            "type": "PURCHASE_REDEEMED",
            "redeemed_from": ["$RCAnonymousID:web", "rc-app-user"],
            "redeemed_by": ["$RCAnonymousID:web", "rc-app-user"],
        },
    )
    assert binding.provider_app_user_ids == ["$RCAnonymousID:web", "rc-app-user"]
    assert binding.redeemer_uid is None
    assert binding.redemption_confirmed_at is not None


@pytest.mark.asyncio
async def test_webhook_preserves_existing_firebase_binding_and_unions_aliases():
    binding = _binding(
        original_app_user_id="$RCAnonymousID:web",
        provider_app_user_ids=["old-alias"],
        redeemer_uid="firebase-uid",
    )
    session = Session(binding, _lead())

    assert await WebFunnelRedemptionService().record_webhook_redemption(
        session,
        {
            "type": "PURCHASE_REDEEMED",
            "redeemed_from": ["$RCAnonymousID:web"],
            "redeemed_by": ["$RCAnonymousID:web", "new-alias"],
        },
    )
    assert binding.provider_app_user_ids == [
        "$RCAnonymousID:web",
        "new-alias",
        "old-alias",
    ]
    assert binding.redeemer_uid == "firebase-uid"


@pytest.mark.asyncio
async def test_finalization_uses_jsonb_containment_for_provider_aliases():
    session = StatementCaptureSession()

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            session,
            uid="firebase-uid",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-1",
            environment="SANDBOX",
        )

    assert error.value.status_code == 404
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "CAST(web_funnel_redemptions.provider_app_user_ids AS JSONB) @>" in sql
    assert "provider_app_user_ids LIKE" not in sql


@pytest.mark.asyncio
async def test_finalization_rejects_user_different_from_legacy_preflight_binding():
    binding = _binding(
        original_app_user_id="$RCAnonymousID:web",
        preflight_uid="verified-user",
    )

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            FinalizationSession(binding, _lead(), None, None),
            uid="different-user",
            email=None,
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-preflight-binding",
            environment="SANDBOX",
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_finalization_identifies_existing_account_recovery():
    binding = _binding(original_app_user_id="$RCAnonymousID:web")
    owner = User(
        firebase_uid="existing-user",
        email="buyer@example.com",
        onboarding_completed=False,
    )

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            FinalizationSession(binding, _lead(), None, owner),
            uid="anonymous-user",
            email=None,
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-existing-account",
            environment="SANDBOX",
        )

    assert error.value.status_code == 409
    assert error.value.detail == {
        "code": "EXISTING_ACCOUNT_REQUIRES_SIGN_IN",
        "message": "Sign in to the existing Nutree account to continue.",
    }


@pytest.mark.asyncio
async def test_finalization_keeps_completed_account_conflict_generic():
    binding = _binding(original_app_user_id="$RCAnonymousID:web")
    owner = User(
        firebase_uid="existing-user",
        email="buyer@example.com",
        onboarding_completed=True,
    )

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            FinalizationSession(binding, _lead(), None, owner),
            uid="anonymous-user",
            email=None,
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-completed-account",
            environment="SANDBOX",
        )

    assert error.value.status_code == 409
    assert error.value.detail == "Claim conflict"
