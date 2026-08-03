"""Infrastructure persistence for web-funnel redemptions."""

import hashlib
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)
from src.infra.services.web_funnel_redemption_completion import finalize_redemption


class WebFunnelRedemptionService:
    """Database adapter used from the API composition root."""

    async def finalize(self, *args, **kwargs):
        return await finalize_redemption(*args, **kwargs)

    async def issue_preflight_token(self, db, binding: WebFunnelRedemption) -> str:
        """Rotate the opaque proof delivered beside the short-lived redemption URL."""
        token = secrets.token_urlsafe(32)
        binding.preflight_token_hash = hashlib.sha256(token.encode()).hexdigest()
        binding.preflight_token_expires_at = utc_now() + timedelta(minutes=60)
        await db.commit()
        return token

    async def preflight(self, db, *, uid: str, email: str, token: str) -> bool:
        """Bind a matching verified Firebase identity without disclosing checkout email."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        binding = await db.scalar(
            select(WebFunnelRedemption)
            .where(WebFunnelRedemption.preflight_token_hash == token_hash)
            .with_for_update()
        )
        if not binding or not binding.preflight_token_expires_at:
            return False
        if binding.preflight_token_expires_at < utc_now():
            return False
        lead = await db.get(WebFunnelLead, binding.lead_id, with_for_update=True)
        if not lead or lead.email.lower() != email.lower():
            return False
        if binding.preflight_uid and binding.preflight_uid != uid:
            return False
        binding.preflight_uid = uid
        binding.preflight_at = utc_now()
        await db.commit()
        return True

    async def record_webhook_redemption(self, db, event: dict) -> bool:
        if event.get("type") != "PURCHASE_REDEEMED":
            return False
        originals = _event_values(event, "redeemed_from")
        original = event.get("original_app_user_id")
        if isinstance(original, str):
            originals.add(original)
        redeemers = _event_values(event, "redeemed_by")
        if not originals or len(redeemers) != 1:
            return False
        binding = await db.scalar(
            select(WebFunnelRedemption)
            .where(WebFunnelRedemption.original_app_user_id.in_(originals))
            .with_for_update()
        )
        if not binding:
            return False
        redeemer_uid = next(iter(redeemers))
        if binding.redeemer_uid and binding.redeemer_uid != redeemer_uid:
            raise HTTPException(status_code=409, detail="Redemption already bound")
        binding.redeemer_uid = redeemer_uid
        binding.redemption_confirmed_at = utc_now()
        return True


def _event_values(event: dict, name: str) -> set[str]:
    value = event.get(name)
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()
