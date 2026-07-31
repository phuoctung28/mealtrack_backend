"""Paddle webhook delivery endpoint."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from src.app.services.paddle_billing_service import PaddleBillingService
from src.bootstrap.paddle_billing import get_paddle_billing_service
from src.domain.exceptions.paddle_billing_exceptions import PaddleWebhookRetryError

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


def _get_paddle_billing_service() -> PaddleBillingService:
    return get_paddle_billing_service()


@router.post("/paddle", status_code=status.HTTP_200_OK)
async def receive_paddle_webhook(request: Request) -> dict[str, str]:
    """Verify and persist a Paddle event using its unparsed request body."""
    raw_body = await request.body()
    billing_service = _get_paddle_billing_service()

    try:
        signature_is_valid = billing_service.verify_webhook_signature(
            raw_body, request.headers
        )
    except RuntimeError as exc:
        logger.error("Paddle webhook is not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification is not configured",
        ) from exc
    except Exception:
        logger.warning("Paddle webhook signature verification failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Paddle webhook signature",
        ) from None

    if not signature_is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Paddle webhook signature",
        )

    try:
        return await billing_service.process_webhook(raw_body)
    except PaddleWebhookRetryError as exc:
        logger.info("Paddle webhook will be retried: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paddle webhook dependency is not available yet",
        ) from exc
    except ValueError as exc:
        logger.warning("Paddle webhook payload was invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Paddle webhook payload",
        ) from exc
