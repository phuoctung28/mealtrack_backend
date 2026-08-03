"""Composition root for web-funnel redemption persistence."""

from src.infra.adapters.revenuecat_adapter import RevenueCatAdapter
from src.infra.config.settings import settings
from src.infra.services.web_funnel_redemption_service import WebFunnelRedemptionService


def get_web_funnel_redemption_service() -> WebFunnelRedemptionService:
    return WebFunnelRedemptionService()


def get_web_funnel_subscription_service() -> RevenueCatAdapter:
    """Use the dedicated key for the configured web-funnel RevenueCat project."""
    return RevenueCatAdapter(api_key=settings.WEB_FUNNEL_REVENUECAT_SECRET_API_KEY or "")
