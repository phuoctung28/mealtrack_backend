"""
Premium access validation middleware.

Uses RevenueCat as source of truth, with local cache for performance.
"""
import logging
import os

from fastapi import Request, HTTPException, status

from src.domain.services.revenuecat_service import RevenueCatService

logger = logging.getLogger(__name__)


async def require_premium(request: Request):
    """
    Dependency that requires active premium subscription.
    
    Strategy:
    1. Check local database cache first (fast)
    2. If no cache, verify with RevenueCat API (accurate)
    
    Usage:
        @router.get("/premium-feature", dependencies=[Depends(require_premium)])
        async def premium_feature():
            return {"data": "premium content"}
    """
    user = getattr(request.state, 'user', None)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Quick check: Local database cache
    if user.is_premium():
        logger.debug(f"User {user.id} has cached premium subscription")
        return
    
    # No local subscription - verify with RevenueCat (source of truth)
    logger.info(f"User {user.id} has no cached subscription, checking RevenueCat")
    
    revenuecat_secret_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
    if not revenuecat_secret_key:
        logger.warning("REVENUECAT_SECRET_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Premium subscription required",
                "error_code": "PREMIUM_REQUIRED"
            }
        )
    
    revenuecat = RevenueCatService(revenuecat_secret_key)
    is_premium = await revenuecat.is_premium_active(app_user_id=user.id)
    
    if is_premium:
        # User has premium in RevenueCat but not in local cache
        # This can happen if webhook failed or is delayed
        logger.warning(f"User {user.id} has premium in RevenueCat but not in cache")
        # Allow access - webhook will sync eventually
        return
    
    # User does not have premium access
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Premium subscription required",
            "error_code": "PREMIUM_REQUIRED"
        }
    )


async def get_premium_status(request: Request) -> dict:
    """
    Non-blocking premium check that returns status info.
    
    Usage:
        @router.get("/feature")
        async def feature(premium_info: dict = Depends(get_premium_status)):
            if premium_info["is_premium"]:
                return {"data": "premium"}
            else:
                return {"data": "basic"}
    """
    user = getattr(request.state, 'user', None)
    
    if not user:
        return {
            "is_premium": False,
            "subscription": None,
            "source": "no_user"
        }
    
    # Check local cache
    subscription = user.get_active_subscription()
    
    if subscription:
        return {
            "is_premium": True,
            "subscription": {
                "product_id": subscription.product_id,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "is_monthly": subscription.is_monthly(),
                "is_yearly": subscription.is_yearly()
            },
            "source": "cache"
        }
    
    # Check RevenueCat if configured
    revenuecat_secret_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
    if revenuecat_secret_key:
        revenuecat = RevenueCatService(revenuecat_secret_key)
        sub_info = await revenuecat.get_subscription_info(user.id)
        
        if sub_info:
            return {
                "is_premium": True,
                "subscription": sub_info,
                "source": "revenuecat_api"
            }
    
    return {
        "is_premium": False,
        "subscription": None,
        "source": "none"
    }