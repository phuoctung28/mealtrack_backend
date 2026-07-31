"""Authenticated Paddle customer billing routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from src.api.dependencies.auth import get_current_user_id
from src.app.services.paddle_billing_service import PaddleBillingService
from src.bootstrap.paddle_billing import get_paddle_billing_service
from src.domain.exceptions.paddle_billing_exceptions import PaddleCustomerNotFoundError

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


def _get_paddle_billing_service() -> PaddleBillingService:
    return get_paddle_billing_service()


@router.get("/paddle/customer-portal")
async def redirect_to_paddle_customer_portal(
    user_id: str = Depends(get_current_user_id),
) -> RedirectResponse:
    """Mint a Paddle-hosted customer portal session for the signed-in user."""
    try:
        portal_url = await _get_paddle_billing_service().create_customer_portal_url(
            user_id
        )
    except PaddleCustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Paddle customer is linked to this account",
        ) from exc
    return RedirectResponse(portal_url, status_code=status.HTTP_303_SEE_OTHER)
