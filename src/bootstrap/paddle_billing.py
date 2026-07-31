"""Paddle billing composition root."""

from src.app.services.paddle_billing_service import PaddleBillingService
from src.infra.services.paddle_billing_gateway import PaddleBillingGateway


def get_paddle_billing_service() -> PaddleBillingService:
    """Construct the application service with its Paddle infrastructure adapter."""
    return PaddleBillingService(PaddleBillingGateway())
