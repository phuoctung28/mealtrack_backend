"""Outbox handler that publishes cache invalidation events to Cloudflare Queue."""

from __future__ import annotations

from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxHandlerResult,
)
from src.infra.adapters.cloudflare_queue_publisher import (
    CloudflareQueueConfigurationError,
    CloudflareQueuePermanentError,
    CloudflareQueuePublisher,
    CloudflareQueueTransientError,
)


class CacheInvalidationQueueHandler:
    """Publish one already-validated cache event to Cloudflare Queue."""

    def __init__(self, publisher: CloudflareQueuePublisher) -> None:
        self._publisher = publisher

    async def handle(
        self,
        payload: dict[str, Any],
        context: OutboxEventContext,
    ) -> OutboxHandlerResult:
        try:
            await self._publisher.publish(payload)
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
                "Unexpected Queue publisher failure",
                error_type=type(exc).__name__,
            )

        return OutboxHandlerResult.ok(
            metadata={"event_id": context.event_id, "destination": "cloudflare_queue"}
        )
