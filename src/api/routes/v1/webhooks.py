"""
Webhook handlers for RevenueCat events.

Syncs subscription data to local database.
"""
import hmac
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: Optional[str] = Header(None)
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
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Extract event data
    event = payload.get("event", {})
    event_type = event.get("type")
    app_user_id = event.get("app_user_id")
    
    logger.error(f"RevenueCat webhook received: {event_type} for app_user_id={app_user_id}")

    # Get user
    from sqlalchemy import select

    async with AsyncUnitOfWork() as uow:
        # Try firebase_uid first (primary lookup path)
        result = await uow.session.execute(
            select(User).where(User.firebase_uid == app_user_id)
        )
        user = result.scalars().first()

        # Fallback: try matching by internal user ID (UUID)
        if not user:
            result = await uow.session.execute(select(User).where(User.id == app_user_id))
            user = result.scalars().first()

        # Fallback: try aliases from event payload (RevenueCat may send anonymous ID)
        if not user:
            aliases = event.get("aliases", [])
            for alias in aliases:
                if alias != app_user_id:
                    result = await uow.session.execute(
                        select(User).where(User.firebase_uid == alias)
                    )
                    user = result.scalars().first()
                    if not user:
                        result = await uow.session.execute(select(User).where(User.id == alias))
                        user = result.scalars().first()
                    if user:
                        break

        if not user:
            logger.error(
                f"RevenueCat webhook: user not found — "
                f"event_type={event_type}, app_user_id={app_user_id}, "
                f"aliases={event.get('aliases', [])}, product_id={event.get('product_id')}"
            )
            raise HTTPException(status_code=404, detail="User not found")
        
        # Handle events
        try:
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

            else:
                logger.info(f"Unhandled event type: {event_type}")

            await uow.commit()
            
        except Exception as e:
            logger.error(
                f"RevenueCat webhook handler error — "
                f"event_type={event_type}, user_id={user.id}, error={e}"
            )
            await uow.rollback()
            raise
    
    return {"status": "success"}


async def handle_purchase(uow, user, event):
    """Handle initial purchase."""
    logger.info(f"Creating subscription for user {user.id}")

    # Check if subscription already exists
    existing = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

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


async def handle_renewal(uow, user, event):
    """Handle subscription renewal."""
    subscription = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

    if subscription:
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} renewed subscription until {subscription.expires_at}")
    else:
        logger.warning(f"Subscription not found for renewal, creating new one")
        await handle_purchase(uow, user, event)


async def handle_cancellation(uow, user, event):
    """Handle subscription cancellation."""
    subscription = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

    if subscription:
        subscription.status = "cancelled"
        subscription.cancelled_at = utc_now()
        subscription.updated_at = utc_now()
        # Note: User still has access until expires_at
        logger.info(f"User {user.id} cancelled subscription (expires {subscription.expires_at})")


async def handle_expiration(uow, user, event):
    """Handle subscription expiration."""
    subscription = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

    if subscription:
        subscription.status = "expired"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} subscription expired")


async def handle_billing_issue(uow, user, event):
    """Handle billing issues."""
    subscription = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

    if subscription:
        subscription.status = "billing_issue"
        subscription.updated_at = utc_now()
        logger.warning(f"Billing issue for user {user.id}")


async def handle_product_change(uow, user, event):
    """Handle product change (e.g., monthly to yearly)."""
    subscription = await get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )

    if subscription:
        subscription.product_id = event.get("product_id")
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} changed to {subscription.product_id}")


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


def parse_timestamp(ms: Optional[int]) -> Optional[datetime]:
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