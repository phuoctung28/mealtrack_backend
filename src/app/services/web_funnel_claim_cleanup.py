"""Repair abandoned provisional Firebase identities after reservation expiry."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.web_funnel_claim_common import utcnow
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_claim import WebFunnelClaim
from src.infra.services.web_funnel_firebase_identity import (
    WebFunnelFirebaseIdentityService,
)


async def cleanup_expired_reservations(
    db: AsyncSession,
    firebase: WebFunnelFirebaseIdentityService | None = None,
    limit: int = 25,
) -> int:
    """Revoke abandoned claims after best-effort removal of their isolated identity."""
    firebase = firebase or WebFunnelFirebaseIdentityService()
    claims = (
        await db.scalars(
            select(WebFunnelClaim)
            .where(
                WebFunnelClaim.reservation_uid.is_not(None),
                WebFunnelClaim.reservation_expires_at < utcnow(),
                WebFunnelClaim.consumed_at.is_(None),
                WebFunnelClaim.revoked_at.is_(None),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).all()
    removed = 0
    for claim in claims:
        if claim.provisional_reservation_uid != claim.reservation_uid:
            claim.revoked_at = utcnow()
            continue
        user = await db.scalar(
            select(User.id).where(User.firebase_uid == claim.reservation_uid)
        )
        if user:
            claim.revoked_at = utcnow()
            continue
        try:
            await firebase.delete_unclaimed_provisional(claim.reservation_uid)
        except Exception:
            continue
        claim.revoked_at = utcnow()
        removed += 1
    await db.commit()
    return removed
