"""Public web funnel checkout routes."""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.web_funnel_requests import (
    PayPalConfirmationRequest,
    WebFunnelCheckoutRequest,
    WebFunnelClaimRequest,
)
from src.api.schemas.response.web_funnel_responses import (
    CheckoutResponse,
    CheckoutStatusResponse,
    WebFunnelClaimResponse,
)
from src.app.services.web_funnel_checkout_service import WebFunnelCheckoutService
from src.infra.adapters.paypal_billing_adapter import PayPalBillingAdapter
from src.infra.config.settings import settings
from src.infra.database.uow_async import AsyncUnitOfWork

router = APIRouter(prefix="/v1/web-funnel", tags=["Web Funnel"])


def _offer_amount(offer: dict, key: str, fallback: int) -> int:
    return int(offer.get(key, fallback) or fallback)


def _checkout_response(checkout, custom_id: str) -> CheckoutResponse:
    offer = settings.web_funnel_paypal_offers.get(checkout.offer_id, {})
    return CheckoutResponse(
        checkout_id=checkout.id,
        status=checkout.state.upper(),
        provider=checkout.provider,
        plan_id=checkout.provider_plan_id,
        custom_id=custom_id,
        offer_id=checkout.offer_id,
        reward_id=checkout.reward_id,
        currency=checkout.currency,
        amount_minor=checkout.amount_minor,
        standard_amount_minor=_offer_amount(
            offer, "standard_amount_minor", checkout.amount_minor
        ),
        renewal_amount_minor=_offer_amount(
            offer, "renewal_amount_minor", checkout.amount_minor
        ),
        renewal_description=str(
            offer.get("renewal_description") or checkout.renewal_interval
        ),
        renewal_interval=checkout.renewal_interval,
        welcome_discount_percent=checkout.welcome_discount_percent,
    )


def _status_response(checkout, claim_token: str | None = None) -> CheckoutStatusResponse:
    return CheckoutStatusResponse(
        checkout_id=checkout.id,
        status=checkout.state.upper(),
        provider=checkout.provider,
        claimable=checkout.state == "paid_active",
        claimed=checkout.claimed_at is not None,
        paid_at=checkout.paid_at,
        claim_token=claim_token if checkout.state == "paid_active" else None,
    )


@router.post("/checkouts", response_model=CheckoutResponse)
@limiter.limit("20/minute")
async def create_checkout(request: Request, body: WebFunnelCheckoutRequest):
    """Create or reuse a server-owned web funnel checkout."""
    service = WebFunnelCheckoutService(settings)
    async with AsyncUnitOfWork() as uow:
        checkout, custom_id = await service.create_checkout(
            uow=uow,
            lead_id=body.lead_id,
            offer_id=body.offer_id,
            reward_id=body.reward_id,
            billing_country=body.billing_country,
            idempotency_key=body.idempotency_key,
        )
        return _checkout_response(checkout, custom_id)


@router.post(
    "/checkouts/{checkout_id}/paypal-confirmation",
    response_model=CheckoutStatusResponse,
)
@limiter.limit("20/minute")
async def confirm_paypal_subscription(
    request: Request, checkout_id: str, body: PayPalConfirmationRequest
):
    """Record browser PayPal approval as a pending provider reference."""
    service = WebFunnelCheckoutService(settings)
    paypal = PayPalBillingAdapter(settings)
    async with AsyncUnitOfWork() as uow:
        checkout = await uow.web_funnel_checkouts.find_by_id(checkout_id)
        if not checkout:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        if checkout.provider_subscription_id == body.subscription_id:
            claim_token = service.claim_token_for_checkout(checkout)
            return _status_response(checkout, claim_token)
        if checkout.state not in {"pending_approval", "pending_payment"}:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409, detail={"error_code": "CHECKOUT_NOT_CONFIRMABLE"}
            )

    snapshot = await paypal.get_subscription(body.subscription_id)

    async with AsyncUnitOfWork() as uow:
        await service.validate_paypal_subscription(
            uow=uow,
            checkout_id=checkout_id,
            subscription_id=body.subscription_id,
            snapshot=snapshot,
        )
        checkout = await service.bind_validated_paypal_subscription(
            uow=uow,
            checkout_id=checkout_id,
            subscription_id=body.subscription_id,
            snapshot=snapshot,
        )
        claim_token = service.claim_token_for_checkout(checkout)
        return _status_response(checkout, claim_token)


@router.get("/checkouts/{checkout_id}", response_model=CheckoutStatusResponse)
@limiter.limit("60/minute")
async def get_checkout_status(request: Request, checkout_id: str):
    """Return safe status for browser polling."""
    async with AsyncUnitOfWork() as uow:
        checkout = await uow.web_funnel_checkouts.find_by_id(checkout_id)
        if not checkout:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        claim_token = WebFunnelCheckoutService(settings).claim_token_for_checkout(
            checkout
        )
        return _status_response(checkout, claim_token)


@router.post("/claims", response_model=WebFunnelClaimResponse)
@limiter.limit("20/minute")
async def claim_checkout(
    request: Request,
    body: WebFunnelClaimRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Consume a one-time paid checkout claim token for the current user."""
    service = WebFunnelCheckoutService(settings)
    async with AsyncUnitOfWork() as uow:
        subscription = await service.claim_checkout(
            uow=uow, user_id=user_id, claim_token=body.claim_token
        )
        return WebFunnelClaimResponse(
            status="claimed", subscription_id=subscription.id
        )
