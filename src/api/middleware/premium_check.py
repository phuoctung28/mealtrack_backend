"""
Subscription access validation middleware.

Uses the local database as the sole source of truth.
RevenueCat webhooks keep the DB in sync; no live RC API calls are made here.
"""

import logging
from datetime import timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user_id
from src.domain.utils.timezone_utils import utc_now
from src.infra.config.settings import settings
from src.infra.database.config_async import get_async_db
from src.infra.database.models.subscription import Subscription

logger = logging.getLogger(__name__)


def _has_subscription_access(subscriptions: list, grace_period_hours: int) -> bool:
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


async def require_subscription(
    user_id: str = Depends(get_current_user_id),
    async_db: AsyncSession = Depends(get_async_db),
) -> None:
    """
    FastAPI dependency that requires an active subscription.

    Resolves user identity via Firebase JWT, then checks subscription state
    in the local database. No RevenueCat API calls.

    Usage:
        router = APIRouter(dependencies=[Depends(require_subscription)])
    """
    if settings.ENVIRONMENT == "development":
        return

    result = await async_db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()

    if _has_subscription_access(subscriptions, settings.SUBSCRIPTION_GRACE_PERIOD_HOURS):
        return

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Standard subscription required",
            "error_code": "SUBSCRIPTION_REQUIRED",
        },
    )


async def get_subscription_status(
    user_id: str = Depends(get_current_user_id),
    async_db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Non-blocking subscription check that returns status info.

    Usage:
        @router.get("/feature")
        async def feature(status_info: dict = Depends(get_subscription_status)):
            if status_info["has_subscription"]:
                return {"data": "premium content"}
    """
    result = await async_db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.purchased_at.desc())
    )
    subscriptions = result.scalars().all()

    # Find the most informative subscription for display (active first, then grace-period states)
    for sub in subscriptions:
        if sub.status == "active" and (sub.expires_at is None or sub.expires_at > utc_now()):
            return {
                "has_subscription": True,
                "subscription": {
                    "product_id": sub.product_id,
                    "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                    "is_monthly": sub.is_monthly(),
                    "is_yearly": sub.is_yearly(),
                },
                "source": "db",
            }

    # Check grace period / cancelled-within-paid-period access
    if _has_subscription_access(subscriptions, settings.SUBSCRIPTION_GRACE_PERIOD_HOURS):
        # Find the subscription granting access for display
        sub = subscriptions[0] if subscriptions else None
        return {
            "has_subscription": True,
            "subscription": {
                "product_id": sub.product_id if sub else None,
                "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
                "is_monthly": sub.is_monthly() if sub else False,
                "is_yearly": sub.is_yearly() if sub else False,
            },
            "source": "db",
        }

    return {"has_subscription": False, "subscription": None, "source": "db"}
