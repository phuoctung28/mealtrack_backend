"""RevenueCat webhook subscription lifecycle event handlers."""

import logging
import uuid

from sqlalchemy import text

from src.api.base_dependencies import get_subscription_service
from src.api.routes.v1.webhook_lookup_parsing import (
    get_subscription_by_revenuecat_id,
    parse_platform,
    parse_timestamp,
)
from src.api.routes.v1.webhook_referral_funnel import (
    credit_referral_on_purchase,
    revoke_referral_on_refund,
)
from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.adapters.posthog_adapter import PostHogAdapter
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.database.models.subscription import Subscription
from src.infra.services.email_template_renderer import EmailTemplateRenderer

logger = logging.getLogger(__name__)

POSTHOG_LIFECYCLE_EVENTS = {
    "CANCELLATION": "subscription_cancelled",
    "EXPIRATION": "subscription_expired",
    "BILLING_ISSUE": "subscription_billing_issue",
    "REFUND": "subscription_refunded",
    "RENEWAL": "subscription_renewed",
    "PRODUCT_CHANGE": "subscription_product_changed",
}


def _get_email_service() -> EmailService:
    """Get email service instance."""
    adapter = ResendEmailAdapter()
    renderer = EmailTemplateRenderer()
    return EmailService(email_adapter=adapter, template_renderer=renderer)


def _get_subscription_service():
    """Resolve the RevenueCat service through the existing dependency boundary."""
    return get_subscription_service()


async def handle_purchase(uow, user, event):
    """Handle initial purchase."""
    logger.info(f"Creating subscription for user {user.id}")

    # Check if subscription already exists
    existing = await get_subscription_by_revenuecat_id(uow, event.get("app_user_id"))

    if existing:
        logger.warning(f"Subscription already exists for {user.id}, updating instead")
        await handle_renewal(uow, user, event)
        return

    # Create new subscription record
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        revenuecat_subscriber_id=event.get("app_user_id"),
        product_id=event.get("product_id"),
        platform=parse_platform(event.get("store")),
        status="active",
        purchased_at=parse_timestamp(event.get("purchased_at_ms")) or utc_now(),
        expires_at=parse_timestamp(event.get("expiration_at_ms")),
        store_transaction_id=event.get("transaction_id"),
        is_sandbox=event.get("environment") == "SANDBOX",
    )

    uow.session.add(subscription)
    logger.info(f"User {user.id} purchased {subscription.product_id}")

    # Credit referrer if this user has a pending referral conversion
    await credit_referral_on_purchase(uow, str(user.id))
    await uow.affiliate_outbox.enqueue(
        "subscription_initial_purchase",
        {
            "mealtrack_user_id": str(user.id),
            "product_id": event.get("product_id"),
            "period_type": event.get("period_type"),
            "subscription_id": event.get("transaction_id")
            or event.get("original_transaction_id"),
            "occurred_at": (
                parse_timestamp(event.get("purchased_at_ms")) or utc_now()
            ).isoformat(),
        },
        event_id=event.get("id"),
    )


async def handle_renewal(uow, user, event):
    """Handle subscription renewal."""
    subscription = await get_subscription_by_revenuecat_id(
        uow, event.get("app_user_id")
    )

    if subscription:
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = utc_now()
        logger.info(
            f"User {user.id} renewed subscription until {subscription.expires_at}"
        )
    else:
        logger.warning("Subscription not found for renewal, creating new one")
        await handle_purchase(uow, user, event)

    await capture_subscription_lifecycle_event(user, event, "RENEWAL", subscription)
    await uow.affiliate_outbox.enqueue(
        "subscription_renewal",
        {
            "mealtrack_user_id": str(user.id),
            "product_id": event.get("product_id"),
            "period_type": event.get("period_type"),
            "subscription_id": event.get("transaction_id")
            or event.get("original_transaction_id"),
            "occurred_at": (
                parse_timestamp(event.get("purchased_at_ms")) or utc_now()
            ).isoformat(),
        },
        event_id=event.get("id"),
    )

    # Purge any pending trial-expiry pushes so renewed users don't get a
    # "your trial ends tomorrow" push for a sub that just auto-renewed.
    try:
        await uow.session.execute(
            text("""
                DELETE FROM notifications
                WHERE user_id = :uid
                  AND notification_type LIKE 'trial_expiry%'
                  AND status = 'pending'
                """),
            {"uid": user.id},
        )
    except Exception:
        # Do not raise — webhook MUST still ACK so RevenueCat doesn't retry.
        logger.exception(
            "Failed to purge stale trial pushes for user %s after renewal", user.id
        )


async def handle_cancellation(uow, user, event):
    """Handle subscription cancellation."""
    subscription = await get_or_create_subscription(uow, user, event)

    if subscription:
        subscription.status = "cancelled"
        subscription.cancelled_at = utc_now()
        subscription.updated_at = utc_now()
        # Note: User still has access until expires_at
        logger.info(
            f"User {user.id} cancelled subscription (expires {subscription.expires_at})"
        )

    await capture_subscription_lifecycle_event(
        user, event, "CANCELLATION", subscription
    )
    await uow.affiliate_outbox.enqueue(
        "subscription_canceled",
        {
            "mealtrack_user_id": str(user.id),
            "product_id": event.get("product_id"),
            "subscription_id": event.get("transaction_id")
            or event.get("original_transaction_id"),
            "occurred_at": utc_now().isoformat(),
        },
        event_id=event.get("id"),
    )

    # Send cancellation email
    if not user.email_opt_out:
        try:
            email_service = _get_email_service()
            await email_service.send_cancellation_email(user)
            logger.info(f"Cancellation email sent to user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send cancellation email to {user.id}: {e}")


async def handle_expiration(uow, user, event):
    """Handle subscription expiration."""
    subscription = await get_or_create_subscription(uow, user, event)

    if subscription:
        subscription.status = "expired"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} subscription expired")

    await capture_subscription_lifecycle_event(user, event, "EXPIRATION", subscription)
    await uow.affiliate_outbox.enqueue(
        "subscription_expired",
        {
            "mealtrack_user_id": str(user.id),
            "product_id": event.get("product_id"),
            "subscription_id": event.get("transaction_id")
            or event.get("original_transaction_id"),
            "occurred_at": utc_now().isoformat(),
        },
        event_id=event.get("id"),
    )


async def handle_billing_issue(uow, user, event):
    """Handle billing issues."""
    subscription = await get_or_create_subscription(uow, user, event)

    if subscription:
        subscription.status = "billing_issue"
        subscription.updated_at = utc_now()
        logger.warning(f"Billing issue for user {user.id}")

    await capture_subscription_lifecycle_event(
        user, event, "BILLING_ISSUE", subscription
    )


async def handle_product_change(uow, user, event):
    """Handle product change (e.g., monthly to yearly)."""
    subscription = await get_or_create_subscription(uow, user, event)

    if subscription:
        subscription.product_id = event.get("product_id")
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} changed to {subscription.product_id}")

    await capture_subscription_lifecycle_event(
        user, event, "PRODUCT_CHANGE", subscription
    )


async def handle_refund(uow, user, event):
    """Handle refund — update subscription status and revoke referral credit."""
    subscription = await get_or_create_subscription(uow, user, event)
    if subscription:
        subscription.status = "refunded"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} subscription refunded")

    await capture_subscription_lifecycle_event(user, event, "REFUND", subscription)
    await uow.affiliate_outbox.enqueue(
        "subscription_refund",
        {
            "mealtrack_user_id": str(user.id),
            "product_id": event.get("product_id"),
            "subscription_id": event.get("transaction_id")
            or event.get("original_transaction_id"),
            "occurred_at": utc_now().isoformat(),
        },
        event_id=event.get("id"),
    )
    await revoke_referral_on_refund(uow, str(user.id))


async def capture_subscription_lifecycle_event(
    user, event, event_type, subscription
) -> None:
    """Mirror RevenueCat lifecycle webhooks into PostHog when configured."""
    posthog_event = POSTHOG_LIFECYCLE_EVENTS.get(event_type)
    if not posthog_event:
        return

    properties = {
        "revenuecat_event_type": event_type,
        "product_id": event.get("product_id")
        or getattr(subscription, "product_id", None),
        "platform": parse_platform(event.get("store")),
        "store": event.get("store"),
        "environment": event.get("environment"),
        "subscription_status": getattr(subscription, "status", None),
        "expiration_at_ms": event.get("expiration_at_ms"),
        "purchased_at_ms": event.get("purchased_at_ms"),
        "cancel_reason": event.get("cancel_reason"),
        "period_type": event.get("period_type"),
        "is_sandbox": event.get("environment") == "SANDBOX",
    }
    await PostHogAdapter().capture(
        distinct_id=getattr(user, "firebase_uid", None) or str(user.id),
        event=posthog_event,
        properties={
            key: value for key, value in properties.items() if value is not None
        },
    )


async def get_or_create_subscription(uow, user, event):
    """Get existing subscription or create one if missing (handles missed INITIAL_PURCHASE)."""
    subscription = await uow.subscriptions.find_by_revenuecat_id(
        event.get("app_user_id")
    )

    if not subscription:
        logger.warning(
            f"No subscription found for user {user.id}, creating record (missed INITIAL_PURCHASE)"
        )
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user.id,
            revenuecat_subscriber_id=event.get("app_user_id"),
            product_id=event.get("product_id") or "unknown",
            platform=parse_platform(event.get("store")),
            status="active",
            purchased_at=parse_timestamp(event.get("purchased_at_ms")) or utc_now(),
            expires_at=parse_timestamp(event.get("expiration_at_ms")),
            store_transaction_id=event.get("transaction_id"),
            is_sandbox=event.get("environment") == "SANDBOX",
        )
        uow.session.add(subscription)
        await uow.session.flush()

    return subscription
