"""Public, browser-capability-protected web-funnel lead drafts."""

import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.api.dependencies.auth import verify_firebase_token
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.web_funnel_requests import (
    CompleteWebFunnelClaimRequest,
    CreateWebFunnelLeadRequest,
)
from src.api.schemas.response.web_funnel_responses import (
    WebFunnelClaimRecoveryResponse,
    WebFunnelClaimResultResponse,
    WebFunnelLeadCreatedResponse,
    WebFunnelLeadStatusResponse,
)
from src.domain.model.web_funnel_handoff import (
    hash_lead_access_key,
    mask_claim_email,
    normalize_claim_email,
    verify_lead_access_key,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.adapters.revenuecat_web_funnel_claim_adapter import (
    RevenueCatWebFunnelClaimAdapter,
)
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_handoff import WebFunnelClaim, WebFunnelLead
from src.infra.database.uow_async import AsyncUnitOfWork

_MAX_LEAD_BODY_BYTES = 16 * 1024


class _LeadBodyLimitRoute(APIRoute):
    """Reject oversized public lead bodies before FastAPI parses their JSON."""

    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def body_limited_handler(request: Request) -> Response:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    body_size = int(content_length)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request body too large",
                    ) from exc
                if body_size > _MAX_LEAD_BODY_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request body too large",
                    )

            original_receive = request._receive
            received_bytes = 0

            async def receive_with_limit() -> dict:
                nonlocal received_bytes
                message = await original_receive()
                if message["type"] == "http.request":
                    received_bytes += len(message.get("body", b""))
                    if received_bytes > _MAX_LEAD_BODY_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Request body too large",
                        )
                return message

            request._receive = receive_with_limit
            return await original_handler(request)

        return body_limited_handler


router = APIRouter(
    prefix="/v1/web-funnel", tags=["Web Funnel"], route_class=_LeadBodyLimitRoute
)

_DRAFT_ACCESS_HEADER = "X-Lead-Access-Key"
_NOT_FOUND_DETAIL = "Lead not found"
_CLAIM_RETRY_SECONDS = 30


def _not_found() -> HTTPException:
    """Avoid disclosing whether an ID exists or a capability was invalid."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
    )


def _public_ip_rate_limit_key(request: Request) -> str:
    """Rate-limit unauthenticated callers by transport identity only."""
    return get_remote_address(request)


def _parse_lead_id(lead_id: str) -> str:
    """Reject malformed identifiers using the same public not-found response."""
    try:
        parsed = uuid.UUID(lead_id)
    except ValueError as exc:
        raise _not_found() from exc
    if parsed.version != 4:
        raise _not_found()
    return str(parsed)


def _claim_error(code: str) -> HTTPException:
    """Return a stable, non-enumerating claim error."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)


def _verified_claim_identity(token: dict) -> tuple[str, str]:
    """Use only claims from the already verified Firebase bearer token."""
    firebase_uid = token.get("uid")
    email = token.get("email")
    if not isinstance(firebase_uid, str) or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    if token.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Verified email required"
        )
    try:
        return firebase_uid, normalize_claim_email(email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


def _claim_result(
    lead: WebFunnelLead, claim_status: str
) -> WebFunnelClaimResultResponse:
    access_sync_status = getattr(lead, "access_sync_status", "pending")
    retry_after_seconds = (
        _CLAIM_RETRY_SECONDS if access_sync_status == "pending" else None
    )
    return WebFunnelClaimResultResponse(
        claim_status=claim_status,
        access_sync_status=access_sync_status,
        retry_after_seconds=retry_after_seconds,
        plan_snapshot=lead.plan_snapshot,
    )


@router.post(
    "/leads",
    response_model=WebFunnelLeadCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute", key_func=_public_ip_rate_limit_key)
async def create_web_funnel_lead(
    request: Request,
    payload: CreateWebFunnelLeadRequest,
    response: Response,
) -> WebFunnelLeadCreatedResponse:
    """Create a browser-owned unpaid draft and return its key exactly once."""
    try:
        normalized_email = normalize_claim_email(payload.email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email",
        ) from exc

    # token_urlsafe draws 256 random bits and yields a header-safe capability.
    draft_access_key = secrets.token_urlsafe(32)
    lead_id = str(uuid.uuid4())
    lead = WebFunnelLead(
        id=lead_id,
        normalized_email=normalized_email,
        draft_access_key_hash=hash_lead_access_key(draft_access_key),
        source=payload.source,
        source_revision=payload.source_revision,
        state="draft",
        revenuecat_app_user_id=lead_id,
    )

    async with AsyncUnitOfWork() as uow:
        if uow.session is None:
            raise RuntimeError("AsyncUnitOfWork session is not initialized")
        uow.session.add(lead)
        await uow.session.flush()

    # The capability is intentionally header-only, never persisted or repeated by
    # the status route. These directives keep browsers and intermediaries from
    # storing the one-time response.
    response.headers[_DRAFT_ACCESS_HEADER] = draft_access_key
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return WebFunnelLeadCreatedResponse(
        lead_id=lead_id,
        masked_email=mask_claim_email(normalized_email),
        state=lead.state,
    )


@router.get(
    "/leads/{lead_id}/status",
    response_model=WebFunnelLeadStatusResponse,
)
@limiter.limit("60/minute", key_func=_public_ip_rate_limit_key)
async def get_web_funnel_lead_status(
    request: Request,
    lead_id: str,
    response: Response,
    x_lead_access_key: str | None = Header(None, alias=_DRAFT_ACCESS_HEADER),
) -> WebFunnelLeadStatusResponse:
    """Return a safe lead state only to the browser holding the draft capability."""
    normalized_lead_id = _parse_lead_id(lead_id)
    if not x_lead_access_key:
        raise _not_found()

    async with AsyncUnitOfWork() as uow:
        if uow.session is None:
            raise RuntimeError("AsyncUnitOfWork session is not initialized")
        result = await uow.session.execute(
            select(WebFunnelLead).where(WebFunnelLead.id == normalized_lead_id)
        )
        lead = result.scalar_one_or_none()

    if lead is None or not verify_lead_access_key(
        x_lead_access_key, lead.draft_access_key_hash
    ):
        raise _not_found()

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return WebFunnelLeadStatusResponse(
        lead_id=lead.id,
        masked_email=mask_claim_email(lead.normalized_email),
        state=lead.state,
    )


@router.post("/claims/complete", response_model=WebFunnelClaimResultResponse)
async def complete_web_funnel_claim(
    payload: CompleteWebFunnelClaimRequest,
    response: Response,
    token: dict = Depends(verify_firebase_token),
) -> WebFunnelClaimResultResponse:
    """Consume a claim capability for its authenticated Firebase owner.

    The token is the only request-body field and is hashed before any database
    lookup. Account identity is never accepted from a sync-style request body.
    """
    firebase_uid, verified_email = _verified_claim_identity(token)
    token_hash = hash_lead_access_key(payload.claim_token)

    async with AsyncUnitOfWork() as uow:
        if uow.session is None:
            raise RuntimeError("AsyncUnitOfWork session is not initialized")
        claim_result = await uow.session.execute(
            select(WebFunnelClaim)
            .where(WebFunnelClaim.token_hash == token_hash)
            .with_for_update()
        )
        claim = claim_result.scalar_one_or_none()
        if claim is None:
            raise _claim_error("claim_revoked")

        lead_result = await uow.session.execute(
            select(WebFunnelLead)
            .where(WebFunnelLead.id == claim.lead_id)
            .with_for_update()
        )
        lead = lead_result.scalar_one_or_none()
        if lead is None:
            raise _claim_error("claim_revoked")

        user_result = await uow.session.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        user = user_result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise _claim_error("claim_account_recovery_required")
        if normalize_claim_email(user.email) != verified_email:
            raise _claim_error("claim_email_mismatch")
        if lead.normalized_email != verified_email:
            raise _claim_error("claim_email_mismatch")

        if claim.claimed_user_id:
            if claim.claimed_user_id != user.id:
                raise _claim_error("claim_consumed_by_other")
            response.headers["Cache-Control"] = "no-store"
            return _claim_result(lead, "already_claimed")

        if claim.status != "active" or claim.expires_at <= utc_now():
            raise _claim_error("claim_expired")
        if getattr(lead, "access_sync_status", "pending") == "refunded":
            raise _claim_error("claim_refunded")

        claim.claimed_user_id = user.id
        claim.status = "consumed"
        claim.consumed_at = utc_now()
        lead.claimed_at = claim.consumed_at
        lead.state = "claimed"
        lead.access_sync_status = "pending"

    # Provider I/O is intentionally outside the claim transaction. The current
    # adapter is fail-safe pending until RevenueCat receipt fulfillment exists.
    sync_status = await RevenueCatWebFunnelClaimAdapter().redeem(
        app_user_id=firebase_uid,
        transaction_id=lead.revenuecat_transaction_id,
    )
    if sync_status != "pending":
        async with AsyncUnitOfWork() as uow:
            if uow.session is None:
                raise RuntimeError("AsyncUnitOfWork session is not initialized")
            result = await uow.session.execute(
                select(WebFunnelLead)
                .where(WebFunnelLead.id == lead.id)
                .with_for_update()
            )
            persisted_lead = result.scalar_one_or_none()
            if persisted_lead is not None:
                persisted_lead.access_sync_status = sync_status
                lead = persisted_lead

    response.headers["Cache-Control"] = "no-store"
    return _claim_result(lead, "claimed")


@router.get("/claims/recovery", response_model=WebFunnelClaimRecoveryResponse)
async def get_web_funnel_claim_recovery(
    response: Response,
    token: dict = Depends(verify_firebase_token),
) -> WebFunnelClaimRecoveryResponse:
    """Project the caller's latest claim without exposing lead or receipt data."""
    firebase_uid, _ = _verified_claim_identity(token)
    async with AsyncUnitOfWork() as uow:
        if uow.session is None:
            raise RuntimeError("AsyncUnitOfWork session is not initialized")
        result = await uow.session.execute(
            select(WebFunnelLead)
            .join(WebFunnelClaim, WebFunnelClaim.lead_id == WebFunnelLead.id)
            .join(User, User.id == WebFunnelClaim.claimed_user_id)
            .where(User.firebase_uid == firebase_uid)
            .order_by(WebFunnelClaim.consumed_at.desc())
            .limit(1)
        )
        lead = result.scalar_one_or_none()

    response.headers["Cache-Control"] = "no-store"
    if lead is None:
        return WebFunnelClaimRecoveryResponse(status="none")
    access_sync_status = getattr(lead, "access_sync_status", "pending")
    return WebFunnelClaimRecoveryResponse(
        status=access_sync_status,
        retry_after_seconds=(
            _CLAIM_RETRY_SECONDS if access_sync_status == "pending" else None
        ),
        plan_ready=lead.plan_snapshot is not None,
    )
