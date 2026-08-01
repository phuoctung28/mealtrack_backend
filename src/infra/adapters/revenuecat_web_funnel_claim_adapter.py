"""Narrow RevenueCat seam for web-funnel receipt association.

The current rollout intentionally has no configured receipt fulfillment path.
Keeping that state explicit lets a paid claim remain recoverable without ever
falling back to Paddle SDK access from this flow.
"""

import os
from typing import Literal

WebFunnelAccessSyncStatus = Literal["pending", "active", "refunded"]


class RevenueCatWebFunnelClaimAdapter:
    """Provider boundary for a future RevenueCat-only receipt redemption worker."""

    async def redeem(
        self,
        *,
        app_user_id: str,
        transaction_id: str | None,
    ) -> WebFunnelAccessSyncStatus:
        """Return pending until RevenueCat Paddle redemption is configured.

        `app_user_id` and `transaction_id` are accepted only at this boundary so
        routes/services cannot gain a direct Paddle fulfillment path.
        """
        del app_user_id, transaction_id
        if not os.getenv("REVENUECAT_PADDLE_PUBLIC_API_KEY"):
            return "pending"
        # The receipt-association API integration is deliberately not enabled by
        # configuration alone. A future worker must implement it here and verify
        # the resulting RevenueCat `standard` entitlement before returning active.
        return "pending"
