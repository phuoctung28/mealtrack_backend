"""Provider-neutral values used by the Paddle billing boundary."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PaddleSubscriptionStatus:
    """The Paddle fields required by API entitlement responses."""

    product_id: str
    price_id: str | None
    status: str
    expires_at: datetime | None
