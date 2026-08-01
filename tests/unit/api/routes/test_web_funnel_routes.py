"""Focused contract tests for public web-funnel lead drafts."""

import uuid
from datetime import timedelta

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request

from src.api.routes.v1 import web_funnel
from src.api.schemas.request.web_funnel_requests import (
    CompleteWebFunnelClaimRequest,
    CreateWebFunnelLeadRequest,
)
from src.domain.model.web_funnel_handoff import (
    hash_lead_access_key,
    verify_lead_access_key,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_handoff import WebFunnelClaim, WebFunnelLead


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _FakeSession:
    def __init__(self) -> None:
        self.lead: object | None = None

    def add(self, lead: object) -> None:
        self.lead = lead

    async def flush(self) -> None:
        return None

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.lead)


class _FakeUnitOfWork:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> "_FakeUnitOfWork":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _SequenceSession:
    def __init__(self, values: list[object | None]) -> None:
        self._values = values

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self._values.pop(0))


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/web-funnel/leads",
            "headers": headers or [],
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "client": ("127.0.0.1", 1234),
        }
    )


@pytest.mark.asyncio
async def test_create_returns_capability_once_in_no_store_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    monkeypatch.setattr(web_funnel, "AsyncUnitOfWork", lambda: _FakeUnitOfWork(session))
    response = Response()

    created = await web_funnel.create_web_funnel_lead(
        _request(), CreateWebFunnelLeadRequest(email="  Person@Example.com "), response
    )

    capability = response.headers["X-Lead-Access-Key"]
    assert uuid.UUID(created.lead_id).version == 4
    assert created.masked_email == "pe***@example.com"
    assert created.state == "draft"
    assert response.headers["Cache-Control"] == "no-store"
    assert capability not in created.model_dump_json()
    assert session.lead is not None
    assert session.lead.revenuecat_app_user_id == created.lead_id
    assert session.lead.draft_access_key_hash != capability
    assert verify_lead_access_key(capability, session.lead.draft_access_key_hash)


@pytest.mark.asyncio
async def test_status_requires_the_draft_capability_and_never_returns_raw_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    monkeypatch.setattr(web_funnel, "AsyncUnitOfWork", lambda: _FakeUnitOfWork(session))
    create_response = Response()
    created = await web_funnel.create_web_funnel_lead(
        _request(),
        CreateWebFunnelLeadRequest(email="person@example.com"),
        create_response,
    )

    status_response = Response()
    result = await web_funnel.get_web_funnel_lead_status(
        _request(),
        created.lead_id,
        status_response,
        create_response.headers["X-Lead-Access-Key"],
    )

    serialized = result.model_dump_json()
    assert result.masked_email == "pe***@example.com"
    assert "person@example.com" not in serialized
    assert "revenuecat" not in serialized.lower()
    assert create_response.headers["X-Lead-Access-Key"] not in serialized
    assert status_response.headers["Cache-Control"] == "no-store"

    with pytest.raises(HTTPException) as exc_info:
        await web_funnel.get_web_funnel_lead_status(
            _request(), created.lead_id, Response(), "wrong-key"
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Lead not found"


@pytest.mark.asyncio
async def test_status_uses_generic_not_found_for_bad_identifier_or_missing_key() -> (
    None
):
    with pytest.raises(HTTPException) as malformed:
        await web_funnel.get_web_funnel_lead_status(
            _request(), "not-a-uuid", Response(), "present"
        )
    with pytest.raises(HTTPException) as missing_capability:
        await web_funnel.get_web_funnel_lead_status(
            _request(), str(uuid.uuid4()), Response(), None
        )

    assert malformed.value.status_code == missing_capability.value.status_code == 404
    assert malformed.value.detail == missing_capability.value.detail == "Lead not found"


def test_create_request_rejects_unallowlisted_fields() -> None:
    with pytest.raises(ValidationError):
        CreateWebFunnelLeadRequest(
            email="person@example.com", payment_credential="secret"
        )


def test_lead_route_rejects_oversized_body_before_request_parsing() -> None:
    app = FastAPI()
    app.include_router(web_funnel.router)

    response = TestClient(app).post(
        "/v1/web-funnel/leads",
        json={"email": "person@example.com", "unexpected": "x" * 16384},
    )

    assert response.status_code == 413


def test_public_rate_limit_key_ignores_unverified_bearer_subjects() -> None:
    first = _request(headers=[(b"authorization", b"Bearer fake.first.payload")])
    second = _request(headers=[(b"authorization", b"Bearer fake.second.payload")])

    assert web_funnel._public_ip_rate_limit_key(first) == "127.0.0.1"
    assert web_funnel._public_ip_rate_limit_key(
        first
    ) == web_funnel._public_ip_rate_limit_key(second)


@pytest.mark.asyncio
async def test_complete_claim_uses_verified_identity_and_replays_for_same_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = WebFunnelLead(
        id=str(uuid.uuid4()),
        normalized_email="person@example.com",
        draft_access_key_hash="draft-hash",
        source="nutree_web_funnel",
        source_revision="v1",
        state="claim_email_sent",
        revenuecat_app_user_id=str(uuid.uuid4()),
        access_sync_status="pending",
        plan_snapshot={"schema_version": "plan_snapshot_v1"},
    )
    claim = WebFunnelClaim(
        lead_id=lead.id,
        generation=1,
        token_hash=hash_lead_access_key("opaque-token"),
        status="active",
        expires_at=utc_now() + timedelta(minutes=5),
    )
    user = User(
        id=str(uuid.uuid4()),
        firebase_uid="firebase-uid",
        email="person@example.com",
        username="person",
        password_hash="not-used",
        is_active=True,
    )
    session = _SequenceSession([claim, lead, user])
    monkeypatch.setattr(web_funnel, "AsyncUnitOfWork", lambda: _FakeUnitOfWork(session))

    completed = await web_funnel.complete_web_funnel_claim(
        CompleteWebFunnelClaimRequest(claim_token="opaque-token"),
        Response(),
        {"uid": "firebase-uid", "email": "person@example.com", "email_verified": True},
    )

    assert completed.model_dump() == {
        "schema_version": "claim_result_v1",
        "claim_status": "claimed",
        "access_sync_status": "pending",
        "retry_after_seconds": 30,
        "plan_snapshot": {"schema_version": "plan_snapshot_v1"},
    }
    assert claim.claimed_user_id == user.id
    assert claim.status == "consumed"
    assert lead.state == "claimed"

    replay_session = _SequenceSession([claim, lead, user])
    monkeypatch.setattr(
        web_funnel, "AsyncUnitOfWork", lambda: _FakeUnitOfWork(replay_session)
    )
    replay = await web_funnel.complete_web_funnel_claim(
        CompleteWebFunnelClaimRequest(claim_token="opaque-token"),
        Response(),
        {"uid": "firebase-uid", "email": "person@example.com", "email_verified": True},
    )
    assert replay.claim_status == "already_claimed"


def test_claim_request_accepts_only_the_opaque_capability() -> None:
    with pytest.raises(ValidationError):
        CompleteWebFunnelClaimRequest(
            claim_token="opaque-token", firebase_uid="attacker-controlled"
        )


@pytest.mark.asyncio
async def test_claim_recovery_returns_only_safe_pending_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = WebFunnelLead(
        id=str(uuid.uuid4()),
        normalized_email="person@example.com",
        draft_access_key_hash="draft-hash",
        source="nutree_web_funnel",
        source_revision="v1",
        state="claimed",
        revenuecat_app_user_id="temporary-revenuecat-id",
        revenuecat_transaction_id="sensitive-transaction",
        access_sync_status="pending",
        plan_snapshot={"schema_version": "plan_snapshot_v1"},
    )
    session = _SequenceSession([lead])
    monkeypatch.setattr(web_funnel, "AsyncUnitOfWork", lambda: _FakeUnitOfWork(session))

    result = await web_funnel.get_web_funnel_claim_recovery(
        Response(),
        {"uid": "firebase-uid", "email": "person@example.com", "email_verified": True},
    )

    assert result.model_dump() == {
        "status": "pending",
        "retry_after_seconds": 30,
        "plan_ready": True,
    }
    assert "transaction" not in result.model_dump_json()
    assert "person@example.com" not in result.model_dump_json()
