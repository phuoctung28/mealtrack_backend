"""
Webhook handlers for RevenueCat events.

Syncs subscription data to local database.
"""
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header

from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow import UnitOfWork

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
    
    # Verify authorization (if configured)
    webhook_secret = os.getenv("REVENUECAT_WEBHOOK_SECRET", "")
    if webhook_secret:
        if authorization != webhook_secret:
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
    
    logger.info(f"RevenueCat webhook: {event_type} for user {app_user_id}")
    
    # Get user
    with UnitOfWork() as uow:
        # Find user by firebase_uid (app_user_id from RevenueCat)
        user = uow.session.query(User).filter_by(firebase_uid=app_user_id).first()
        if not user:
            logger.warning(f"User not found: {app_user_id}")
            return {"status": "user_not_found"}
        
        # Handle events
        try:
            if event_type == "INITIAL_PURCHASE":
                handle_purchase(uow, user, event)
                
            elif event_type == "RENEWAL":
                handle_renewal(uow, user, event)
                
            elif event_type == "CANCELLATION":
                handle_cancellation(uow, user, event)
                
            elif event_type == "EXPIRATION":
                handle_expiration(uow, user, event)
                
            elif event_type == "BILLING_ISSUE":
                handle_billing_issue(uow, user, event)
                
            elif event_type == "PRODUCT_CHANGE":
                handle_product_change(uow, user, event)
            
            else:
                logger.info(f"Unhandled event type: {event_type}")
            
            uow.commit()
            
        except Exception as e:
            logger.error(f"Error handling webhook event {event_type}: {e}")
            uow.rollback()
            raise
    
    return {"status": "success"}


def handle_purchase(uow, user, event):
    """Handle initial purchase."""
    logger.info(f"Creating subscription for user {user.id}")
    
    # Check if subscription already exists
    existing = get_subscription_by_revenuecat_id(
        uow, 
        event.get("app_user_id")
    )
    
    if existing:
        logger.warning(f"Subscription already exists for {user.id}, updating instead")
        handle_renewal(uow, user, event)
        return
    
    # Create new subscription record
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        revenuecat_subscriber_id=event.get("app_user_id"),
        product_id=event.get("product_id"),
        platform=parse_platform(event.get("store")),
        status="active",
        purchased_at=parse_timestamp(event.get("purchased_at_ms")) or datetime.now(),
        expires_at=parse_timestamp(event.get("expiration_at_ms")),
        store_transaction_id=event.get("transaction_id"),
        is_sandbox=event.get("environment") == "SANDBOX",
    )
    
    uow.session.add(subscription)
    logger.info(f"User {user.id} purchased {subscription.product_id}")


def handle_renewal(uow, user, event):
    """Handle subscription renewal."""
    subscription = get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )
    
    if subscription:
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = datetime.now()
        logger.info(f"User {user.id} renewed subscription until {subscription.expires_at}")
    else:
        logger.warning(f"Subscription not found for renewal, creating new one")
        handle_purchase(uow, user, event)


def handle_cancellation(uow, user, event):
    """Handle subscription cancellation."""
    subscription = get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )
    
    if subscription:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now()
        subscription.updated_at = datetime.now()
        # Note: User still has access until expires_at
        logger.info(f"User {user.id} cancelled subscription (expires {subscription.expires_at})")


def handle_expiration(uow, user, event):
    """Handle subscription expiration."""
    subscription = get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )
    
    if subscription:
        subscription.status = "expired"
        subscription.updated_at = datetime.now()
        logger.info(f"User {user.id} subscription expired")


def handle_billing_issue(uow, user, event):
    """Handle billing issues."""
    subscription = get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )
    
    if subscription:
        subscription.status = "billing_issue"
        subscription.updated_at = datetime.now()
        logger.warning(f"Billing issue for user {user.id}")
        # TODO: Send notification to user


def handle_product_change(uow, user, event):
    """Handle product change (e.g., monthly to yearly)."""
    subscription = get_subscription_by_revenuecat_id(
        uow,
        event.get("app_user_id")
    )
    
    if subscription:
        subscription.product_id = event.get("product_id")
        subscription.expires_at = parse_timestamp(event.get("expiration_at_ms"))
        subscription.status = "active"
        subscription.updated_at = datetime.now()
        logger.info(f"User {user.id} changed to {subscription.product_id}")


def get_subscription_by_revenuecat_id(uow, revenuecat_id: str):
    """Get subscription by RevenueCat subscriber ID."""
    return uow.subscriptions.get_by_revenuecat_id(revenuecat_id)


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
        return datetime.fromtimestamp(ms / 1000)
    except Exception as e:
        logger.error(f"Error parsing timestamp {ms}: {e}")
        return None


@router.get("/revenuecat/health")
async def webhook_health():
    """Health check for webhook."""
    return {"status": "ok", "service": "revenuecat_webhook"}