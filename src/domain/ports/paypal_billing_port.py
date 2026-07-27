"""Port for PayPal subscription billing operations."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PayPalSubscriptionSnapshot:
    """Safe subscription fields needed for checkout validation."""

    id: str
    plan_id: str | None
    custom_id: str | None
    status: str | None
    merchant_id: str | None = None
    subscriber_id: str | None = None
    currency: str | None = None
    amount_minor: int | None = None


@dataclass(frozen=True)
class PayPalWebhookVerification:
    """Result of provider-side webhook signature verification."""

    verified: bool
    event_id: str | None = None
    event_type: str | None = None
    resource_id: str | None = None


class PayPalBillingPort(Protocol):
    """Provider interface for PayPal subscription APIs."""

    async def get_subscription(
        self, subscription_id: str
    ) -> PayPalSubscriptionSnapshot:
        """Fetch a subscription from PayPal."""

    async def verify_webhook(
        self, headers: dict[str, str], raw_body: bytes
    ) -> PayPalWebhookVerification:
        """Verify a PayPal webhook signature with PayPal."""
