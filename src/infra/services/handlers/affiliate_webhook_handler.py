"""Affiliate webhook outbox event handler wrapping AffiliateServiceAdapter."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.domain.ports.affiliate_service_port import AffiliateServicePort
from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.adapters.affiliate_service_adapter import AffiliateServiceAdapter

logger = logging.getLogger(__name__)


class AffiliateWebhookHandler(OutboxEventHandler):
    """Dispatches affiliate lifecycle webhooks with HMAC-SHA256 signatures."""

    def __init__(self, adapter: AffiliateServicePort | None = None) -> None:
        self._adapter = adapter or AffiliateServiceAdapter()

    async def handle(
        self,
        payload: dict[str, Any],
        context: OutboxEventContext,
    ) -> OutboxHandlerResult:
        if not isinstance(payload, dict):
            return OutboxHandlerResult.permanent_failure(
                "Payload must be a dictionary",
                error_type="InvalidPayload",
            )

        try:
            success = await self._adapter.send_event(payload)
            if success:
                return OutboxHandlerResult.ok(
                    metadata={"event_type": context.event_type}
                )
            return OutboxHandlerResult.transient_failure(
                "Affiliate webhook send failed or returned non-200 status",
                error_type="AffiliateDeliveryError",
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if 400 <= status_code < 500 and status_code != 429:
                return OutboxHandlerResult.permanent_failure(
                    f"Affiliate API client error: HTTP {status_code}",
                    error_type="HTTPClientError",
                    status_code=status_code,
                )
            return OutboxHandlerResult.transient_failure(
                f"Affiliate API server error: HTTP {status_code}",
                error_type="HTTPServerError",
                status_code=status_code,
            )
        except httpx.TimeoutException:
            return OutboxHandlerResult.transient_failure(
                "Affiliate API request timed out",
                error_type="TimeoutException",
            )
        except httpx.HTTPError as exc:
            return OutboxHandlerResult.transient_failure(
                f"Affiliate API network error: {exc}",
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            logger.exception("Unexpected error in AffiliateWebhookHandler")
            return OutboxHandlerResult.transient_failure(
                f"Unexpected error: {exc}",
                error_type=type(exc).__name__,
            )
