"""
Subscription access validation middleware.

Uses RevenueCat as source of truth, with local cache for performance.
"""

import logging
import os
from typing import Optional

from fastapi import Request, HTTPException, status

from src.domain.ports.subscription_service_port import SubscriptionServicePort
from src.api.base_dependencies import get_subscription_service

logger = logging.getLogger(__name__)


def _get_subscription_service() -> SubscriptionServicePort:
    """Helper to get subscription service - can be overridden in tests."""
    return get_subscription_service()


async def require_subscription(request: Request):
    """
    Dependency that requires active standard subscription.

    Strategy:
    1. Check local database cache first (fast)
    2. If no cache, verify with RevenueCat API (accurate)

    Usage:
        @router.get("/subscription-feature", dependencies=[Depends(require_subscription)])
        async def subscription_feature():
            return {"data": "subscription content"}
    """
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # Quick check: Local database cache
    if user.has_active_subscription():
        logger.debug(f"User {user.id} has cached subscription")
        return

    # No local subscription - verify with RevenueCat (source of truth)
    logger.info(f"User {user.id} has no cached subscription, checking RevenueCat")

    revenuecat_secret_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
    if not revenuecat_secret_key:
        logger.warning("REVENUECAT_SECRET_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Standard subscription required",
                "error_code": "SUBSCRIPTION_REQUIRED",
            },
        )

    subscription_service = _get_subscription_service()
    has_subscription = await subscription_service.has_active_subscription(
        app_user_id=user.firebase_uid
    )

    if has_subscription:
        # User has subscription in RevenueCat but not in local cache
        # This can happen if webhook failed or is delayed
        logger.warning(
            f"User {user.id} has subscription in RevenueCat but not in cache"
        )
        # Allow access - webhook will sync eventually
        return

    # User does not have subscription access
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Standard subscription required",
            "error_code": "SUBSCRIPTION_REQUIRED",
        },
    )


async def get_subscription_status(request: Request) -> dict:
    """
    Non-blocking subscription check that returns status info.

    Usage:
        @router.get("/feature")
        async def feature(status_info: dict = Depends(get_subscription_status)):
            if status_info["has_subscription"]:
                return {"data": "subscription"}
            else:
                return {"data": "basic"}
    """
    user = getattr(request.state, "user", None)

    if not user:
        return {"has_subscription": False, "subscription": None, "source": "no_user"}

    # Check local cache
    subscription = user.get_active_subscription()

    if subscription:
        return {
            "has_subscription": True,
            "subscription": {
                "product_id": subscription.product_id,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
                "is_monthly": subscription.is_monthly(),
                "is_yearly": subscription.is_yearly(),
            },
            "source": "cache",
        }

    # Check RevenueCat if configured
    revenuecat_secret_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
    if revenuecat_secret_key:
        subscription_service = _get_subscription_service()
        sub_info = await subscription_service.get_subscription_info(user.id)

        if sub_info:
            return {
                "has_subscription": True,
                "subscription": sub_info,
                "source": "revenuecat_api",
            }

    return {"has_subscription": False, "subscription": None, "source": "none"}
