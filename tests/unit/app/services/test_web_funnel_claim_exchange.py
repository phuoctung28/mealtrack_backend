"""Single-use exchange tests keep all browser secrets out of persistence."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from src.app.services.web_funnel_claim_common import hash_secret, utcnow
from src.app.services.web_funnel_claim_exchange import exchange_claim
from src.infra.database.models.web_funnel_claim import WebFunnelClaim, WebFunnelLead
from src.infra.services.web_funnel_firebase_identity import (
    FirebaseIdentity,
    FirebaseIdentityConflict,
)


class FakeExchangeSession:
    def __init__(self, claim, lead):
        self.claim, self.lead = claim, lead
        self.commits = 0

    async def scalar(self, _statement):
        return self.claim

    async def get(self, _model, _id, **_kwargs):
        return self.lead

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


class FakeFirebase:
    def __init__(self):
        self.is_provisional = True

    async def resolve(self, _lead_id, email):
        return FirebaseIdentity(
            uid="wf-uid", email=email, is_provisional=self.is_provisional
        )

    async def mint_custom_token(self, _identity, _reservation_id, _generation):
        return "firebase-custom-token"


class ConflictFirebase:
    async def resolve(self, _lead_id, _email):
        raise FirebaseIdentityConflict()


@pytest.mark.asyncio
async def test_exchange_reserves_claim_and_persists_hashes_not_returned_secrets():
    magic, retry = "m" * 48, "r" * 48
    lead = WebFunnelLead(
        id="lead-1",
        email="buyer@example.com",
        access_key_hash="key",
        request_id="request",
        snapshot_version="v1",
        snapshot={},
        snapshot_hash="snapshot",
        status="email_queued",
        revision=1,
        access_sync_status="pending",
    )
    claim = WebFunnelClaim(
        id="claim-1",
        lead_id="lead-1",
        generation=1,
        magic_token_hash=hash_secret(magic),
        expires_at=utcnow() + timedelta(hours=1),
    )
    response = await exchange_claim(
        FakeExchangeSession(claim, lead), magic, retry, FakeFirebase()
    )
    assert response["firebase_custom_token"] == "firebase-custom-token"
    assert response["exchange_token"] not in {magic, retry}
    assert claim.reservation_retry_secret_hash == hash_secret(retry)
    assert claim.exchange_token_hash == hash_secret(response["exchange_token"])
    assert claim.provisional_reservation_uid == "wf-uid"


@pytest.mark.asyncio
async def test_exchange_retry_retains_provisional_cleanup_ownership():
    magic, retry = "m" * 48, "r" * 48
    lead = WebFunnelLead(
        id="lead-1",
        email="buyer@example.com",
        access_key_hash="key",
        request_id="request",
        snapshot_version="v1",
        snapshot={},
        snapshot_hash="snapshot",
        status="email_queued",
        revision=1,
        access_sync_status="pending",
    )
    claim = WebFunnelClaim(
        id="claim-1",
        lead_id="lead-1",
        generation=1,
        magic_token_hash=hash_secret(magic),
        expires_at=utcnow() + timedelta(hours=1),
    )
    firebase = FakeFirebase()
    session = FakeExchangeSession(claim, lead)
    await exchange_claim(session, magic, retry, firebase)
    firebase.is_provisional = False
    await exchange_claim(session, magic, retry, firebase)
    assert claim.provisional_reservation_uid == "wf-uid"
    assert lead.status == "claim_reserved"


@pytest.mark.asyncio
async def test_exchange_persists_terminal_conflict_after_reservation_commit():
    magic, retry = "m" * 48, "r" * 48
    lead = WebFunnelLead(
        id="lead-1",
        email="buyer@example.com",
        access_key_hash="key",
        request_id="request",
        snapshot_version="v1",
        snapshot={},
        snapshot_hash="snapshot",
        status="email_queued",
        revision=1,
        access_sync_status="pending",
    )
    claim = WebFunnelClaim(
        id="claim-1",
        lead_id="lead-1",
        generation=1,
        magic_token_hash=hash_secret(magic),
        expires_at=utcnow() + timedelta(hours=1),
    )
    session = FakeExchangeSession(claim, lead)

    with pytest.raises(HTTPException) as exc:
        await exchange_claim(session, magic, retry, ConflictFirebase())

    assert exc.value.status_code == 409
    assert session.commits == 2
    assert lead.status == "conflict"
    assert claim.revoked_at is not None
