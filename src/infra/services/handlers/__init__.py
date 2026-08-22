"""Outbox event handlers package and default registry factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infra.services.handlers.affiliate_webhook_handler import (
    AffiliateWebhookHandler,
)
from src.infra.services.handlers.push_notification_handler import (
    PushNotificationHandler,
)
from src.infra.services.handlers.telemetry_handler import TelemetryHandler
from src.infra.services.outbox_handler_registry import OutboxHandlerRegistry

if TYPE_CHECKING:
    from src.domain.ports.affiliate_service_port import AffiliateServicePort
    from src.infra.adapters.posthog_adapter import PostHogAdapter
    from src.infra.services.firebase_service import FirebaseService

__all__ = [
    "AffiliateWebhookHandler",
    "PushNotificationHandler",
    "TelemetryHandler",
    "create_default_handler_registry",
]


def create_default_handler_registry(
    *,
    affiliate_adapter: AffiliateServicePort | None = None,
    firebase_service: FirebaseService | None = None,
    posthog_adapter: PostHogAdapter | None = None,
) -> OutboxHandlerRegistry:
    """Create and configure an OutboxHandlerRegistry with built-in handlers."""
    registry = OutboxHandlerRegistry()

    affiliate_handler = AffiliateWebhookHandler(affiliate_adapter)
    push_handler = PushNotificationHandler(firebase_service)
    telemetry_handler = TelemetryHandler(posthog_adapter)

    # Affiliate event routes
    for event_type in (
        "affiliate_event",
        "affiliate_webhook",
        "affiliate.referral_created",
        "affiliate.conversion",
    ):
        registry.register(event_type, affiliate_handler)

    # Push notification routes
    for event_type in (
        "push_notification",
        "notification.push",
        "scheduled_push",
    ):
        registry.register(event_type, push_handler)

    # Telemetry and analytics routes
    for event_type in (
        "telemetry_event",
        "analytics.event",
        "posthog.capture",
    ):
        registry.register(event_type, telemetry_handler)

    return registry
