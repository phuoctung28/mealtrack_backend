"""Outbox handler that publishes push notification events to Cloudflare Queue."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.adapters.cloudflare_queue_publisher import (
    CloudflareQueueConfigurationError,
    CloudflareQueuePermanentError,
    CloudflareQueuePublisher,
    CloudflareQueueTransientError,
)

logger = logging.getLogger(__name__)


class PushNotificationQueueHandler(OutboxEventHandler):
    """Publish push notification outbox events to Cloudflare Queue."""

    def __init__(self, publisher: CloudflareQueuePublisher) -> None:
        self._publisher = publisher

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

        # Standardize envelope for Cloudflare Queue consumer
        event_payload = dict(payload)
        if "event_type" not in event_payload:
            event_payload["event_type"] = "push_notification.v1"
        if "version" not in event_payload:
            event_payload["version"] = 1
        if "event_id" not in event_payload:
            event_payload["event_id"] = context.event_id
        if "user_id" not in event_payload and "user_id" in payload:
            event_payload["user_id"] = str(payload["user_id"])
        if "occurred_at" not in event_payload:
            event_payload["occurred_at"] = context.created_at_iso

        try:
            await self._publisher.publish(event_payload)
        except CloudflareQueueTransientError as exc:
            return OutboxHandlerResult.transient_failure(
                str(exc),
                error_type=type(exc).__name__,
            )
        except (
            CloudflareQueueConfigurationError,
            CloudflareQueuePermanentError,
        ) as exc:
            return OutboxHandlerResult.permanent_failure(
                str(exc),
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            return OutboxHandlerResult.transient_failure(
                f"Unexpected Queue publisher failure: {exc}",
                error_type=type(exc).__name__,
            )

        return OutboxHandlerResult.ok(
            metadata={
                "event_id": context.event_id,
                "destination": "cloudflare_queue",
                "queue": self._publisher._queue_name,
            }
        )
