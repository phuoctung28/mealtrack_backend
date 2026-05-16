"""
Subscription access validation middleware.

Uses the local database as the sole source of truth.
RevenueCat webhooks keep the DB in sync; no live RC API calls are made here.
"""

import logging
from datetime import timedelta

from fastapi import Request, HTTPException, status

from src.domain.utils.timezone_utils import utc_now
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


def _has_subscription_access(subscriptions, grace_period_hours: int) -> bool:
    """
    Return True if any subscription in the list grants access.

    Grace period tolerates webhook delivery delays and billing retry windows.
    Intentionally cancelled subscriptions get no grace period — access ends at expires_at.
    """
    now = utc_now()
    grace = timedelta(hours=grace_period_hours)

    for sub in subscriptions:
        if sub.status in ("refunded", "expired"):
            continue

        if sub.status == "active":
            if sub.expires_at is None:
                return True  # Lifetime subscription
            if now <= sub.expires_at + grace:
                return True

        elif sub.status == "cancelled":
            # No grace period — user intentionally cancelled
            if sub.expires_at and now <= sub.expires_at:
                return True

        elif sub.status == "billing_issue":
            # Grace period covers the billing retry window
            if sub.expires_at and now <= sub.expires_at + grace:
                return True

    return False


async def require_subscription(request: Request):
    """
    FastAPI dependency that requires an active subscription.

    Checks the local database only. No RevenueCat API calls.

    Usage:
        router = APIRouter(dependencies=[Depends(require_subscription)])
    """
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Fast path: covers active subscriptions and the dev mock (has_active_subscription=lambda: True)
    if user.has_active_subscription():
        return

    # Grace period path: covers cancelled-within-period and billing_issue cases
    subscriptions = getattr(user, "subscriptions", [])
    if _has_subscription_access(subscriptions, settings.SUBSCRIPTION_GRACE_PERIOD_HOURS):
        logger.debug(f"User {user.id} allowed via grace period / paid-through-period check")
        return

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
                return {"data": "premium content"}
    """
    user = getattr(request.state, "user", None)

    if not user:
        return {"has_subscription": False, "subscription": None, "source": "no_user"}

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

    return {"has_subscription": False, "subscription": None, "source": "none"}
