"""
Webhook handlers for RevenueCat events.

Syncs subscription data to local database.
"""

import hmac
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select, text

from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.adapters.posthog_adapter import PostHogAdapter
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.email_template_renderer import EmailTemplateRenderer

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)

NON_RETRYABLE_USERLESS_EVENTS = {
    "TRANSFER",
    "CANCELLATION",
    "EXPIRATION",
    "BILLING_ISSUE",
    "PRODUCT_CHANGE",
    "REFUND",
}

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


@router.post("/revenuecat")
async def revenuecat_webhook(
    request: Request, authorization: str | None = Header(None)
):
    """
    Handle RevenueCat webhook events.

    This keeps your local database in sync with RevenueCat.
    """

    # Verify webhook is configured - reject if secret not set
    webhook_secret = os.getenv("REVENUECAT_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("RevenueCat webhook not configured - rejecting request")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    # Verify authorization (constant-time comparison to prevent timing attacks)
    if not hmac.compare_digest(authorization or "", webhook_secret):
        logger.warning("Invalid RevenueCat webhook authorization")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # Extract event data
    event = payload.get("event", {})
    event_type = event.get("type")
    app_user_id = event.get("app_user_id")

    logger.info(
        f"RevenueCat webhook received: {event_type} for app_user_id={app_user_id}"
    )

    # Get user
    async with AsyncUnitOfWork() as uow:
        if event_type == "TRANSFER":
            await handle_transfer(uow, event)
            return {"status": "success"}

        user = await find_user_for_revenuecat_event(uow, event)

        if not user:
            logger.error(
                f"RevenueCat webhook: user not found — "
                f"event_type={event_type}, app_user_id={app_user_id}, "
                f"aliases={event.get('aliases', [])}, "
                f"original_app_user_id={event.get('original_app_user_id')}, "
                f"product_id={event.get('product_id')}"
            )
            if event_type in NON_RETRYABLE_USERLESS_EVENTS:
                return {"status": "ignored", "reason": "user_not_found"}
            raise HTTPException(status_code=404, detail="User not found")

        # Handle events — commit/rollback is owned by the AsyncUnitOfWork context manager
        if event_type == "INITIAL_PURCHASE":
            await handle_purchase(uow, user, event)

        elif event_type == "RENEWAL":
            await handle_renewal(uow, user, event)

        elif event_type == "CANCELLATION":
            await handle_cancellation(uow, user, event)

        elif event_type == "EXPIRATION":
            await handle_expiration(uow, user, event)

        elif event_type == "BILLING_ISSUE":
            await handle_billing_issue(uow, user, event)

        elif event_type == "PRODUCT_CHANGE":
            await handle_product_change(uow, user, event)

        elif event_type == "REFUND":
            await handle_refund(uow, user, event)

    return {"status": "success"}


def _candidate_revenuecat_ids(event: dict) -> list[str]:
    """Return RevenueCat IDs worth trying for user/subscription lookup."""
    candidates = [
        event.get("app_user_id"),
        event.get("original_app_user_id"),
        *(event.get("aliases") or []),
        *(event.get("transferred_to") or []),
        *(event.get("transferred_from") or []),
    ]
    seen: set[str] = set()
    return [
        candidate
        for candidate in candidates
        if isinstance(candidate, str)
        and candidate
        and not (candidate in seen or seen.add(candidate))
    ]


async def find_user_for_revenuecat_event(uow, event: dict) -> User | None:
    """Find a user from any RevenueCat identifier present in a webhook payload."""
    for candidate in _candidate_revenuecat_ids(event):
        result = await uow.session.execute(
            select(User).where(User.firebase_uid == candidate)
        )
        user = result.scalars().first()
        if user:
            return user

        # User.id stores UUID values as strings; skip anonymous/non-UUID
        # RevenueCat IDs here so only valid internal IDs hit this fallback.
        try:
            candidate_uuid = uuid.UUID(candidate)
        except (ValueError, AttributeError, TypeError):
            candidate_uuid = None
        if candidate_uuid is not None:
            result = await uow.session.execute(
                select(User).where(User.id == str(candidate_uuid))
            )
            user = result.scalars().first()
            if user:
                return user

        subscription = await uow.subscriptions.find_by_revenuecat_id(candidate)
        if subscription:
            result = await uow.session.execute(
                select(User).where(User.id == subscription.user_id)
            )
            user = result.scalars().first()
            if user:
                logger.info(
                    "RevenueCat webhook: found user via subscription record — "
                    "revenuecat_id=%s, user_id=%s",
                    candidate,
                    user.id,
                )
                return user
    return None


async def handle_transfer(uow, event):
    """Handle RevenueCat subscriber transfers without failing on anonymous IDs."""
    transferred_from = event.get("transferred_from") or []
    transferred_to = event.get("transferred_to") or []
    if not transferred_from or not transferred_to:
        logger.info("RevenueCat transfer ignored: missing transfer IDs")
        return

    subscription = None
    for source_id in transferred_from:
        subscription = await uow.subscriptions.find_by_revenuecat_id(source_id)
        if subscription:
            break

    if not subscription:
        logger.info(
            "RevenueCat transfer ignored: no local subscription matched transferred_from=%s",
            transferred_from,
        )
        return

    target_id = _preferred_transfer_target(transferred_to)
    if not target_id:
        logger.info("RevenueCat transfer ignored: no valid transferred_to ID")
        return

    subscription.revenuecat_subscriber_id = target_id
    subscription.updated_at = utc_now()
    logger.info(
        "RevenueCat transfer updated subscription %s to subscriber_id=%s",
        subscription.id,
        target_id,
    )


def _preferred_transfer_target(transferred_to: list[str]) -> str | None:
    """Prefer a custom app user ID over RevenueCat anonymous IDs."""
    for candidate in transferred_to:
        if (
            isinstance(candidate, str)
            and candidate
            and not candidate.startswith("$RCAnonymousID:")
        ):
            return candidate
    return next(
        (item for item in transferred_to if isinstance(item, str) and item), None
    )


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
    await _credit_referral_on_purchase(uow, str(user.id))


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

    await _revoke_referral_on_refund(uow, str(user.id))


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


async def _credit_referral_on_purchase(uow, user_id: str) -> None:
    """Credit the referrer's wallet when a referred user completes their first purchase."""
    from src.infra.repositories.referral_repository import ReferralRepository

    repo = ReferralRepository(uow.session)
    conversion = await repo.get_conversion_by_referred_user(user_id, for_update=True)
    if conversion and conversion.status == "pending":
        conversion.status = "converted"
        conversion.converted_at = utc_now()
        # Use VND amount for wallet (fallback to commission_amount for old records)
        amount_vnd = conversion.commission_amount_vnd or conversion.commission_amount
        await repo.credit_wallet(conversion.referrer_user_id, amount_vnd)
        logger.info(
            "Referral credited: referrer=%s amount=%d VND (original: %d %s)",
            conversion.referrer_user_id,
            amount_vnd,
            conversion.commission_amount,
            conversion.commission_currency or "VND",
        )


async def _revoke_referral_on_refund(uow, user_id: str) -> None:
    """Revoke the referrer's wallet credit when a referred user is refunded."""
    from src.infra.repositories.referral_repository import ReferralRepository

    repo = ReferralRepository(uow.session)
    conversion = await repo.get_conversion_by_referred_user(user_id, for_update=True)
    if conversion and conversion.status == "converted":
        conversion.status = "revoked"
        conversion.revoked_at = utc_now()
        # Use VND amount for wallet (fallback to commission_amount for old records)
        amount_vnd = conversion.commission_amount_vnd or conversion.commission_amount
        await repo.revoke_from_wallet(conversion.referrer_user_id, amount_vnd)
        logger.info(
            "Referral revoked: referrer=%s amount=%d VND",
            conversion.referrer_user_id,
            amount_vnd,
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


async def get_subscription_by_revenuecat_id(uow, revenuecat_id: str):
    """Get subscription by RevenueCat subscriber ID."""
    return await uow.subscriptions.find_by_revenuecat_id(revenuecat_id)


def parse_platform(store: str) -> str:
    """Parse store name to platform."""
    if not store:
        return "ios"

    store_upper = store.upper()
    store_map = {
        "APP_STORE": "ios",
        "PLAY_STORE": "android",
        "STRIPE": "web",
        "MAC_APP_STORE": "ios",
    }
    return store_map.get(store_upper, "ios")


def parse_timestamp(ms: int | None) -> datetime | None:
    """Parse millisecond timestamp to datetime."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception as e:
        logger.error(f"Error parsing timestamp {ms}: {e}")
        return None


@router.get("/revenuecat/health")
async def webhook_health():
    """Health check for webhook."""
    return {"status": "ok", "service": "revenuecat_webhook"}
