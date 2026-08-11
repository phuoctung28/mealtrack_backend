"""
Webhook handlers for RevenueCat events.

Thin router — business logic lives in sibling modules.
"""

import hmac
import logging
import os
import uuid

from fastapi import APIRouter, Header, HTTPException, Request

from src.api.routes.v1.webhook_lookup_parsing import (
    candidate_revenuecat_ids,
    find_user_for_revenuecat_event,
    is_anonymous_event,
    parse_platform,
    parse_timestamp,
)
from src.api.routes.v1.webhook_referral_funnel import (
    _get_subscription_service,
    credit_referral_on_purchase,
    handle_transfer,
    record_web_funnel_redemption,
    revoke_referral_on_refund,
    sync_redeemed_target_subscription,
)
from src.api.routes.v1.webhook_subscription_lifecycle import (
    handle_billing_issue,
    handle_cancellation,
    handle_expiration,
    handle_product_change,
    handle_purchase,
    handle_refund,
    handle_renewal,
)
from src.app.services.web_funnel_claim_payment import reconcile_revenuecat_event
from src.bootstrap.web_funnel_claim_dispatcher import get_web_funnel_outbox_dispatcher
from src.infra.database.uow_async import AsyncUnitOfWork
from src.observability import increment_metric

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

# Backward-compatible aliases for tests and external imports
_candidate_revenuecat_ids = candidate_revenuecat_ids
_is_anonymous_event = is_anonymous_event
_record_web_funnel_redemption = record_web_funnel_redemption
_credit_referral_on_purchase = credit_referral_on_purchase
_revoke_referral_on_refund = revoke_referral_on_refund

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

    async with AsyncUnitOfWork() as redemption_uow:
        if await record_web_funnel_redemption(redemption_uow, event):
            return {"status": "success"}

    # A paid web lead is deliberately recognized only by an exact backend UUID.
    # It is reconciled from fetched provider state before the native path, which
    # continues untouched for every non-lead event.
    app_user_id = event.get("app_user_id")
    if isinstance(app_user_id, str):
        try:
            lead_id = str(uuid.UUID(app_user_id))
        except ValueError:
            pass
        else:
            async with AsyncUnitOfWork() as web_funnel_uow:
                subscriber = await _get_subscription_service().get_subscriber_info(
                    lead_id
                )
                if await reconcile_revenuecat_event(
                    web_funnel_uow.session, event, subscriber
                ):
                    await get_web_funnel_outbox_dispatcher()(lead_id=lead_id)
                    return {"status": "success"}

    logger.info(
        "RevenueCat webhook received: event_type=%s environment=%s",
        event_type,
        event.get("environment"),
    )

    # Get user
    async with AsyncUnitOfWork() as uow:
        user = await find_user_for_revenuecat_event(uow, event)

        if event_type == "TRANSFER":
            if not user:
                logger.info("RevenueCat transfer ignored: target user not found")
                return {"status": "ignored", "reason": "user_not_found"}
            await handle_transfer(uow, event)
            await sync_redeemed_target_subscription(uow, user, event)
            increment_metric(
                "webhook.revenuecat.processed",
                attributes={"event_type": event_type, "status": "success"},
            )
            return {"status": "success"}

        if event_type == "PURCHASE_REDEEMED":
            if not user:
                logger.info("RevenueCat purchase redemption target user not found")
                raise HTTPException(status_code=404, detail="User not found")
            await sync_redeemed_target_subscription(uow, user, event)
            increment_metric(
                "webhook.revenuecat.processed",
                attributes={"event_type": event_type, "status": "success"},
            )
            return {"status": "success"}

        if not user:
            logger.error(
                "RevenueCat webhook: user not found — event_type=%s "
                "environment=%s id_candidates=%s",
                event_type,
                event.get("environment"),
                len(candidate_revenuecat_ids(event)),
            )
            if event_type in NON_RETRYABLE_USERLESS_EVENTS or is_anonymous_event(event):
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

    increment_metric(
        "webhook.revenuecat.processed",
        attributes={"event_type": event_type or "unknown", "status": "success"},
    )
    return {"status": "success"}


@router.get("/revenuecat/health")
async def webhook_health():
    """Health check for webhook."""
    return {"status": "ok", "service": "revenuecat_webhook"}
