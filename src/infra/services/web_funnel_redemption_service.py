"""Infrastructure persistence for web-funnel redemptions."""

import hashlib

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

    async def preflight(self, db, *, uid: str, email: str, redemption_url: str) -> bool:
        """Bind a matching verified Firebase identity without disclosing checkout email."""
        redemption_link_hash = hashlib.sha256(redemption_url.encode()).hexdigest()
        binding = await db.scalar(
            select(WebFunnelRedemption)
            .where(WebFunnelRedemption.redemption_link_hash == redemption_link_hash)
            .with_for_update()
        )
        if not binding or binding.finalized_uid or binding.redeemer_uid:
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
        if not originals or not redeemers:
            return False
        binding = await db.scalar(
            select(WebFunnelRedemption)
            .where(WebFunnelRedemption.original_app_user_id.in_(originals))
            .with_for_update()
        )
        if not binding:
            return False
        if binding.redeemer_uid and binding.redeemer_uid not in redeemers:
            raise HTTPException(status_code=409, detail="Redemption already bound")
        binding.provider_app_user_ids = sorted(redeemers)
        if len(redeemers) == 1:
            binding.redeemer_uid = next(iter(redeemers))
        binding.redemption_confirmed_at = utc_now()
        return True


def _event_values(event: dict, name: str) -> set[str]:
    value = event.get(name)
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()
