"""Port for Paddle-specific billing operations."""

from abc import ABC, abstractmethod
from collections.abc import Mapping

from src.domain.model.paddle_billing import PaddleSubscriptionStatus


class PaddleBillingPort(ABC):
    """Keeps Paddle SDK and persistence details outside the application layer."""

    @abstractmethod
    def verify_webhook_signature(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> bool:
        """Verify a raw Paddle webhook delivery."""

    @abstractmethod
    async def process_webhook(self, raw_body: bytes) -> dict[str, str]:
        """Persist a verified Paddle webhook delivery."""

    @abstractmethod
    async def user_has_access(self, user_id: str) -> bool:
        """Return whether a user has access from verified Paddle state."""

    @abstractmethod
    async def get_active_subscription(
        self, user_id: str
    ) -> PaddleSubscriptionStatus | None:
        """Return a user's access-granting Paddle subscription."""

    @abstractmethod
    async def create_customer_portal_url(self, user_id: str) -> str:
        """Create a Paddle-hosted portal URL for the authenticated user."""
