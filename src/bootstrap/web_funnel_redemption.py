"""Composition root for web-funnel redemption persistence."""

from src.infra.services.web_funnel_redemption_service import WebFunnelRedemptionService


def get_web_funnel_redemption_service() -> WebFunnelRedemptionService:
    return WebFunnelRedemptionService()
