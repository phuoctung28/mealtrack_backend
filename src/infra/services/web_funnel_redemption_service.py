"""Infrastructure persistence for web-funnel redemptions."""

from fastapi import HTTPException
from sqlalchemy import select

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.web_funnel_claim import WebFunnelRedemption
from src.infra.services.web_funnel_redemption_completion import finalize_redemption


class WebFunnelRedemptionService:
    """Database adapter used from the API composition root."""

    async def finalize(self, *args, **kwargs):
        return await finalize_redemption(*args, **kwargs)

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
