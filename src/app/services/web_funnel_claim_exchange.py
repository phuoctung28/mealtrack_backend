"""Reservation and Firebase custom-token exchange for web funnel claims."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.web_funnel_claim_common import (
    EXCHANGE_TTL,
    RESERVATION_TTL,
    claim_conflict,
    claim_not_found,
    hash_secret,
    new_secret,
    token_matches,
    utcnow,
)
from src.infra.database.models.web_funnel_claim import WebFunnelClaim, WebFunnelLead
from src.infra.services.web_funnel_firebase_identity import (
    FirebaseIdentityConflict,
    WebFunnelFirebaseIdentityService,
)


async def exchange_claim(
    db: AsyncSession,
    magic_token: str,
    retry_secret: str,
    firebase: WebFunnelFirebaseIdentityService | None = None,
) -> dict[str, str]:
    """Reserve a valid claim before external minting; retries require the proof."""
    firebase = firebase or WebFunnelFirebaseIdentityService()
    now = utcnow()
    claim = await db.scalar(
        select(WebFunnelClaim)
        .where(WebFunnelClaim.magic_token_hash == hash_secret(magic_token))
        .with_for_update()
    )
    if not claim or claim.revoked_at or claim.expires_at <= now or claim.consumed_at:
        raise claim_not_found()
    lead = await db.get(WebFunnelLead, claim.lead_id, with_for_update=True)
    if not lead or lead.status in {"refunded", "revoked", "conflict"}:
        raise claim_not_found()

    if claim.reservation_expires_at and claim.reservation_expires_at > now:
        if not token_matches(retry_secret, claim.reservation_retry_secret_hash):
            raise claim_conflict()
    else:
        claim.reservation_id = str(uuid.uuid4())
        claim.reservation_retry_secret_hash = hash_secret(retry_secret)
        claim.reservation_expires_at = now + RESERVATION_TTL
        claim.exchange_token_hash = None
        claim.exchange_expires_at = None
    lead.status = "claim_reserved"
    await db.commit()

    try:
        identity = await firebase.resolve(lead.id, lead.email)
        custom_token = await firebase.mint_custom_token(
            identity, claim.reservation_id, claim.generation
        )
    except FirebaseIdentityConflict:
        await db.rollback()
        raise claim_conflict() from None
    except Exception:
        # The proof-bound reservation remains retryable until it expires.
        await db.rollback()
        raise

    claim = await db.scalar(
        select(WebFunnelClaim).where(WebFunnelClaim.id == claim.id).with_for_update()
    )
    if not claim or claim.reservation_expires_at is None or claim.reservation_expires_at <= utcnow():
        raise claim_not_found()
    if claim.reservation_uid and claim.reservation_uid != identity.uid:
        raise claim_conflict()
    exchange_token = new_secret()
    claim.reservation_uid = identity.uid
    if identity.is_provisional or claim.provisional_reservation_uid == identity.uid:
        claim.provisional_reservation_uid = identity.uid
    claim.exchange_token_hash = hash_secret(exchange_token)
    claim.exchange_expires_at = utcnow() + EXCHANGE_TTL
    await db.commit()
    return {"firebase_custom_token": custom_token, "exchange_token": exchange_token}


def reservation_is_bound(claim: WebFunnelClaim, uid: str, exchange_token: str | None) -> bool:
    """Allow recovery from a custom-token bearer only while its reservation is live."""
    if claim.reservation_uid != uid or not claim.reservation_expires_at:
        return False
    if claim.reservation_expires_at <= utcnow():
        return False
    if exchange_token is None:
        return True
    return bool(
        claim.exchange_expires_at
        and claim.exchange_expires_at > utcnow()
        and token_matches(exchange_token, claim.exchange_token_hash)
    )
