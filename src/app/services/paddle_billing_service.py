"""Application boundary for Paddle billing and fulfillment."""

from collections.abc import Mapping

from src.domain.model.paddle_billing import PaddleSubscriptionStatus
from src.domain.ports.paddle_billing_port import PaddleBillingPort


class PaddleBillingService:
    """Coordinates API requests through the Paddle billing port."""

    def __init__(self, paddle_billing: PaddleBillingPort):
        self._paddle_billing = paddle_billing

    def verify_webhook_signature(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> bool:
        return self._paddle_billing.verify_webhook_signature(raw_body, headers)

    async def process_webhook(self, raw_body: bytes) -> dict[str, str]:
        return await self._paddle_billing.process_webhook(raw_body)

    async def user_has_access(self, user_id: str) -> bool:
        return await self._paddle_billing.user_has_access(user_id)

    async def get_active_subscription(
        self, user_id: str
    ) -> PaddleSubscriptionStatus | None:
        return await self._paddle_billing.get_active_subscription(user_id)

    async def create_customer_portal_url(self, user_id: str) -> str:
        return await self._paddle_billing.create_customer_portal_url(user_id)
