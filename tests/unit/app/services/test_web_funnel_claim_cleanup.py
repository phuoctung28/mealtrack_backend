from datetime import timedelta

import pytest

from src.app.services.web_funnel_claim_cleanup import cleanup_expired_reservations
from src.app.services.web_funnel_claim_common import utcnow
from src.infra.database.models.web_funnel_claim import WebFunnelClaim


class FakeSession:
    def __init__(self, claim, user=None):
        self.claim = claim
        self.user = user
        self.committed = False

    async def scalars(self, _statement):
        class Result:
            def __init__(self, claim):
                self.claim = claim

            def all(self):
                return [self.claim]

        return Result(self.claim)

    async def scalar(self, _statement):
        return self.user

    async def commit(self):
        self.committed = True


class FakeFirebase:
    def __init__(self):
        self.deleted = []

    async def delete_unclaimed_provisional(self, uid):
        self.deleted.append(uid)


@pytest.mark.asyncio
async def test_cleanup_deletes_only_expired_unclaimed_reservation():
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="hash", expires_at=utcnow() + timedelta(hours=1), reservation_uid="wf_provisional", provisional_reservation_uid="wf_provisional", reservation_expires_at=utcnow() - timedelta(minutes=1))
    firebase = FakeFirebase()
    assert await cleanup_expired_reservations(FakeSession(claim), firebase) == 1
    assert firebase.deleted == ["wf_provisional"]
    assert claim.revoked_at is not None


@pytest.mark.asyncio
async def test_cleanup_never_deletes_reused_or_claimed_identity():
    claim = WebFunnelClaim(id="claim-1", lead_id="lead-1", generation=1, magic_token_hash="hash", expires_at=utcnow() + timedelta(hours=1), reservation_uid="wf_existing", reservation_expires_at=utcnow() - timedelta(minutes=1))
    firebase = FakeFirebase()
    assert await cleanup_expired_reservations(FakeSession(claim, user="local-user"), firebase) == 0
    assert firebase.deleted == []
    assert claim.revoked_at is not None
