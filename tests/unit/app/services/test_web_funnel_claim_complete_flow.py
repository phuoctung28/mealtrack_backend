"""Atomic completion creates local state only after a bound exchange reservation."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from src.app.services.web_funnel_claim_common import hash_secret, utcnow
from src.app.services.web_funnel_claim_completion import complete_claim, recover_claim
from src.infra.database.models.web_funnel_claim import WebFunnelClaim, WebFunnelLead


class FakeCompletionSession:
    def __init__(self, claim, lead):
        self.claim, self.lead = claim, lead
        self.added = []
        self.committed = False
        self.scalar_calls = 0

    async def scalar(self, _statement):
        self.scalar_calls += 1
        return self.claim if self.scalar_calls == 1 else None

    async def get(self, _model, _id, **_kwargs):
        return self.lead

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_bound_completion_commits_one_result_and_association_outbox():
    token = "x" * 48
    snapshot = {"birth_year": 1995, "birth_month": 4, "birth_day": 20, "gender": "female", "height": 168, "weight": 62, "job_type": "desk", "training_days_per_week": 3, "training_minutes_per_session": 45, "goal": "recomp"}
    lead = WebFunnelLead(id="lead-1", email="buyer@example.com", access_key_hash="key", request_id="request", snapshot_version="v1", snapshot=snapshot, snapshot_hash="snapshot", status="claim_reserved", revision=1, access_sync_status="pending")
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="magic", expires_at=utcnow() + timedelta(hours=1), reservation_id="reservation-1", reservation_uid="uid-1", reservation_expires_at=utcnow() + timedelta(minutes=5), exchange_token_hash=hash_secret(token), exchange_expires_at=utcnow() + timedelta(minutes=2))
    session = FakeCompletionSession(claim, lead)
    result = await complete_claim(session, "uid-1", "buyer@example.com", token)
    assert result["version"] == "claim_result_v1"
    assert claim.consumed_uid == "uid-1"
    assert lead.status == "claimed"
    assert any(hasattr(item, "weekly_budget_id") for item in session.added)
    assert any(getattr(item, "job_type", None) == "revenuecat_association" for item in session.added)
    assert session.committed


@pytest.mark.asyncio
async def test_same_uid_completion_replay_returns_immutable_result():
    token = "x" * 48
    result = {"version": "claim_result_v1", "access_status": "pending"}
    lead = WebFunnelLead(id="lead-1", email="buyer@example.com", access_key_hash="key", request_id="request", snapshot_version="v1", snapshot={}, snapshot_hash="snapshot", status="claimed", revision=1, access_sync_status="pending")
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="magic", expires_at=utcnow() + timedelta(hours=1), exchange_token_hash=hash_secret(token), consumed_uid="uid-1", consumed_at=utcnow(), result=result)
    assert await complete_claim(FakeCompletionSession(claim, lead), "uid-1", "buyer@example.com", token) == result


@pytest.mark.asyncio
async def test_other_uid_cannot_replay_consumed_claim():
    token = "x" * 48
    lead = WebFunnelLead(id="lead-1", email="buyer@example.com", access_key_hash="key", request_id="request", snapshot_version="v1", snapshot={}, snapshot_hash="snapshot", status="claimed", revision=1, access_sync_status="pending")
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="magic", expires_at=utcnow() + timedelta(hours=1), exchange_token_hash=hash_secret(token), consumed_uid="uid-1", consumed_at=utcnow(), result={"version": "claim_result_v1"})
    with pytest.raises(HTTPException) as error:
        await complete_claim(FakeCompletionSession(claim, lead), "uid-2", "buyer@example.com", token)
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_recovery_returns_only_same_uid_committed_result():
    result = {"version": "claim_result_v1", "access_status": "pending"}
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="magic", expires_at=utcnow() + timedelta(hours=1), reservation_uid="uid-1", consumed_uid="uid-1", consumed_at=utcnow(), result=result)

    class RecoverySession:
        async def scalar(self, _statement):
            return claim

    assert await recover_claim(RecoverySession(), "uid-1", None, None) == result
    with pytest.raises(HTTPException):
        await recover_claim(RecoverySession(), "uid-2", None, None)
