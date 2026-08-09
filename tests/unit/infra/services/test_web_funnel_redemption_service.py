"""Focused safety tests for authenticated RevenueCat redemption."""

import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.domain.model.auth import AuthProvider
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)
from src.infra.services.web_funnel_redemption_completion import (
    finalize_redemption,
    utcnow,
)
from src.infra.services.web_funnel_redemption_service import (
    WebFunnelRedemptionService,
)


class Session:
    def __init__(self, binding, lead):
        self.binding = binding
        self.lead = lead
        self.committed = False

    async def scalar(self, _statement):
        return self.binding

    async def scalars(self, _statement):
        return [self.binding] if self.binding else []

    async def get(self, _model, _identifier, **_kwargs):
        return self.lead

    async def commit(self):
        self.committed = True


class StatementCaptureSession:
    def __init__(self):
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return None

    async def scalars(self, statement):
        self.statements.append(statement)
        return []


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


def _binding(lead_id="lead-1", **values):
    values.setdefault("original_app_user_id", "$RCAnonymousID:web")
    return WebFunnelRedemption(lead_id=lead_id, **values)


def _link_hash(link="rc-example://redeem?token=opaque"):
    return hashlib.sha256(link.encode()).hexdigest()


@pytest.mark.asyncio
async def test_preflight_binds_matching_verified_identity():
    binding = _binding()
    session = Session(binding, _lead())

    assert await WebFunnelRedemptionService().preflight(
        session,
        uid="firebase-uid",
        email="buyer@example.com",
        redemption_link_hash=_link_hash(),
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
        redemption_link_hash=_link_hash("rc-example://unknown"),
    )
    assert not await service.preflight(
        Session(_binding(), _lead()),
        uid="firebase-uid",
        email="other@example.com",
        redemption_link_hash=_link_hash(),
    )


@pytest.mark.asyncio
async def test_preflight_rejects_replayed_redemption_binding():
    assert not await WebFunnelRedemptionService().preflight(
        Session(
            _binding(redeemer_uid="firebase-uid", finalized_uid="firebase-uid"),
            _lead(),
        ),
        uid="firebase-uid",
        email="buyer@example.com",
        redemption_link_hash=_link_hash(),
    )


@pytest.mark.asyncio
async def test_webhook_records_provider_aliases_without_binding_firebase_identity():
    binding = _binding(original_app_user_id="$RCAnonymousID:web")
    session = Session(binding, _lead())

    assert await WebFunnelRedemptionService().record_webhook_redemption(
        session,
        {
            "type": "PURCHASE_REDEEMED",
            "environment": "SANDBOX",
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
            "environment": "SANDBOX",
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
    sql_statements = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.statements
    ]
    assert any(
        "CAST(web_funnel_redemptions.provider_app_user_ids AS JSONB) @>" in sql
        for sql in sql_statements
    )
    assert all("provider_app_user_ids LIKE" not in sql for sql in sql_statements)
    assert all(
        "web_funnel_redemptions.redeemer_uid =" not in sql
        for sql in sql_statements
    )


@pytest.mark.asyncio
async def test_finalization_retry_returns_stored_result_for_same_purchase():
    binding = _binding(
        redeemer_uid="firebase-uid",
        finalized_uid="firebase-uid",
        finalization_key_hash=hashlib.sha256(
            b"request-retry-same-purchase"
        ).hexdigest(),
        result={"version": "redemption_result_v1", "access_status": "active"},
    )

    result = await finalize_redemption(
        FinalizationSession(binding, _lead(), None, None),
        uid="firebase-uid",
        email="buyer@example.com",
        original_app_user_id="$RCAnonymousID:web",
        idempotency_key="request-retry-same-purchase",
        environment="SANDBOX",
    )

    assert result == binding.result


@pytest.mark.asyncio
async def test_finalization_retry_selects_by_idempotency_key_hash():
    key = "request-keyed-retry"
    binding = _binding(
        redeemer_uid="firebase-uid",
        finalized_uid="firebase-uid",
        finalization_key_hash=hashlib.sha256(key.encode()).hexdigest(),
        result={"version": "redemption_result_v1", "access_status": "active"},
    )

    class Session:
        def __init__(self):
            self.statements = []

        async def scalar(self, statement):
            self.statements.append(statement)
            return binding

    session = Session()
    assert (
        await finalize_redemption(
            session,
            uid="firebase-uid",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key=key,
            environment="SANDBOX",
        )
        == binding.result
    )
    assert "finalization_key_hash" in str(
        session.statements[0].compile(dialect=postgresql.dialect())
    )


@pytest.mark.asyncio
async def test_finalization_does_not_reuse_finalized_purchase_for_new_key():
    class Session:
        async def scalar(self, _statement):
            return None

        async def scalars(self, _statement):
            return []

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            Session(),
            uid="firebase-uid",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-different-key",
            environment="SANDBOX",
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_finalization_rechecks_key_after_pending_lock_race():
    key = "request-concurrent-retry"
    binding = _binding(
        redeemer_uid="firebase-uid",
        finalized_uid="firebase-uid",
        finalization_key_hash=hashlib.sha256(key.encode()).hexdigest(),
        result={"version": "redemption_result_v1", "access_status": "active"},
    )

    class Session:
        def __init__(self):
            self.key_lookups = 0

        async def scalar(self, statement):
            sql = str(statement.compile(dialect=postgresql.dialect()))
            if "finalization_key_hash" in sql:
                self.key_lookups += 1
                return binding if self.key_lookups == 2 else None
            return None

        async def scalars(self, _statement):
            return []

    session = Session()
    result = await finalize_redemption(
        session,
        uid="firebase-uid",
        email="buyer@example.com",
        original_app_user_id="$RCAnonymousID:web",
        idempotency_key=key,
        environment="SANDBOX",
    )

    assert result == binding.result
    assert session.key_lookups == 2


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
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-preflight-binding",
            environment="SANDBOX",
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_finalization_rejects_new_link_without_preflight_binding():
    binding = _binding(
        original_app_user_id="$RCAnonymousID:web",
        redemption_link_hash=_link_hash(),
    )

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            FinalizationSession(binding, _lead(), None, None),
            uid="firebase-user",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:web",
            idempotency_key="request-missing-preflight",
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
            email="buyer@example.com",
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
async def test_finalization_attaches_purchase_to_authenticated_user():
    binding = _binding(
        original_app_user_id="$RCAnonymousID:web",
        redemption_link_hash=_link_hash(),
        preflight_uid="google-user",
        product_id="web_monthly",
        environment="SANDBOX",
        provider="revenuecat",
        project="default",
        verified_app_user_id="$RCAnonymousID:web",
        entitlement_id="standard",
        verified_at=utcnow(),
    )
    lead = _lead()
    lead.snapshot = {
        "gender": "female",
        "height": 168,
        "weight": 62,
        "birth_year": 1995,
        "birth_month": 4,
        "birth_day": 20,
        "job_type": "desk",
        "training_days_per_week": 3,
        "training_minutes_per_session": 45,
        "goal": "recomp",
        "target_calories": None,
        "custom_protein_g": None,
        "custom_carbs_g": None,
        "custom_fat_g": None,
    }

    class Session:
        def __init__(self):
            self.scalars = iter([binding, None, None, None, None, None])
            self.added = []

        async def scalar(self, _statement):
            return next(self.scalars)

        async def get(self, _model, _identifier, **_kwargs):
            return lead

        def add(self, item):
            self.added.append(item)

        async def flush(self):
            for item in self.added:
                if isinstance(item, User):
                    item.id = "user-1"

        async def commit(self):
            return None

    session = Session()
    result = await finalize_redemption(
        session,
        uid="google-user",
        email="BUYER@example.com",
        original_app_user_id="$RCAnonymousID:web",
        idempotency_key="request-google-user",
        environment="SANDBOX",
        auth_provider="google.com",
    )

    user = next(item for item in session.added if isinstance(item, User))
    assert user.provider is AuthProvider.GOOGLE
    assert user.firebase_uid == "google-user"
    subscription = next(
        item for item in session.added if isinstance(item, Subscription)
    )
    assert subscription.platform == "web"
    assert result["access_status"] == "active"
    assert result["macros"] == {
        "calories": 2000,
        "protein": 150,
        "carbs": 200,
        "fat": 65,
    }


@pytest.mark.asyncio
async def test_finalization_allows_second_purchase_for_existing_authenticated_user():
    binding = _binding(
        original_app_user_id="$RCAnonymousID:second-purchase",
        redemption_link_hash=_link_hash("rc-example://second-purchase"),
        preflight_uid="existing-user",
        product_id="web_monthly",
        environment="SANDBOX",
        verified_at=utcnow(),
    )
    lead = _lead()
    lead.snapshot = {"target_calories": 2000}
    existing_user = User(
        id="user-1",
        firebase_uid="existing-user",
        email="buyer@example.com",
        onboarding_completed=False,
    )

    class Session:
        def __init__(self):
            self.scalars = iter(
                [
                    binding,
                    existing_user,
                    None,
                    object(),
                    object(),
                    SimpleNamespace(status="active"),
                ]
            )

        async def scalar(self, _statement):
            return next(self.scalars)

        async def get(self, _model, _identifier, **_kwargs):
            return lead

        async def commit(self):
            return None

    result = await finalize_redemption(
        Session(),
        uid="existing-user",
        email="buyer@example.com",
        original_app_user_id="$RCAnonymousID:second-purchase",
        idempotency_key="request-second-purchase",
        environment="SANDBOX",
    )

    assert result["access_status"] == "active"
    assert binding.redeemer_uid == "existing-user"
    assert binding.finalized_uid == "existing-user"


@pytest.mark.asyncio
async def test_finalization_prefers_one_pending_alias_over_older_finalized_purchase():
    old_binding = _binding(
        original_app_user_id="$RCAnonymousID:root",
        provider_app_user_ids=["$RCAnonymousID:root"],
        finalized_uid="existing-user",
        result={"version": "redemption_result_v1", "access_status": "active"},
    )
    new_binding = _binding(
        original_app_user_id="$RCAnonymousID:new",
        provider_app_user_ids=["$RCAnonymousID:root", "$RCAnonymousID:new"],
        preflight_uid="existing-user",
        product_id="web_monthly",
        environment="SANDBOX",
        verified_at=utcnow(),
    )
    lead = _lead()
    lead.snapshot = {"target_calories": 2000}
    existing_user = User(
        id="user-1",
        firebase_uid="existing-user",
        email="buyer@example.com",
        onboarding_completed=True,
    )

    class Session:
        def __init__(self):
            self.pending_lookup_count = 2
            self.scalar_results = iter(
                [existing_user, None, object(), object(), SimpleNamespace(status="active")]
            )

        async def scalar(self, _statement):
            if self.pending_lookup_count:
                self.pending_lookup_count -= 1
                return None
            return next(self.scalar_results)

        async def scalars(self, _statement):
            return [new_binding]

        async def get(self, _model, _identifier, **_kwargs):
            return lead

        async def commit(self):
            return None

    result = await finalize_redemption(
        Session(),
        uid="existing-user",
        email="buyer@example.com",
        original_app_user_id="$RCAnonymousID:root",
        idempotency_key="request-alias-purchase",
        environment="SANDBOX",
    )

    assert result["access_status"] == "active"
    assert old_binding.finalized_uid == "existing-user"
    assert new_binding.finalized_uid == "existing-user"

    new_binding.result = result

    class RetrySession:
        async def scalar(self, _statement):
            return new_binding

    assert (
        await finalize_redemption(
            RetrySession(),
            uid="existing-user",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:root",
            idempotency_key="request-alias-purchase",
            environment="SANDBOX",
        )
        == new_binding.result
    )


@pytest.mark.asyncio
async def test_finalization_rejects_multiple_pending_alias_matches():
    class Session:
        async def scalar(self, _statement):
            return None

        async def scalars(self, _statement):
            return [_binding(), _binding(lead_id="lead-2")]

    with pytest.raises(HTTPException) as error:
        await finalize_redemption(
            Session(),
            uid="existing-user",
            email="buyer@example.com",
            original_app_user_id="$RCAnonymousID:root",
            idempotency_key="request-ambiguous-alias",
            environment="SANDBOX",
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_webhook_rejects_ambiguous_repeat_purchase_aliases():
    first = _binding(original_app_user_id="$RCAnonymousID:first")
    second = _binding(
        lead_id="lead-2", original_app_user_id="$RCAnonymousID:second"
    )

    class Session:
        async def scalars(self, _statement):
            return [first, second]

    recorded = await WebFunnelRedemptionService().record_webhook_redemption(
        Session(),
        {
            "type": "PURCHASE_REDEEMED",
            "environment": "SANDBOX",
            "redeemed_from": [
                "$RCAnonymousID:first",
                "$RCAnonymousID:second",
            ],
            "redeemed_by": ["$RCAnonymousID:canonical"],
        },
    )

    assert not recorded
    assert first.redemption_confirmed_at is None
    assert second.redemption_confirmed_at is None
