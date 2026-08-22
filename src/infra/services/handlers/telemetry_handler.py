"""Telemetry outbox event handler wrapping PostHogAdapter."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.adapters.posthog_adapter import PostHogAdapter

logger = logging.getLogger(__name__)


class TelemetryHandler(OutboxEventHandler):
    """Dispatches background product telemetry events to PostHog."""

    def __init__(self, adapter: PostHogAdapter | None = None) -> None:
        self._adapter = adapter or PostHogAdapter()

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

        distinct_id = payload.get("distinct_id") or payload.get("user_id")
        if not distinct_id or not str(distinct_id).strip():
            return OutboxHandlerResult.permanent_failure(
                "Telemetry payload must include 'distinct_id' or 'user_id'",
                error_type="ValidationError",
            )

        event_name = (
            payload.get("event") or payload.get("event_name") or context.event_type
        )
        properties = payload.get("properties", {})
        if not isinstance(properties, dict):
            return OutboxHandlerResult.permanent_failure(
                "Telemetry properties must be a dictionary",
                error_type="ValidationError",
            )

        try:
            await self._adapter.capture(
                distinct_id=str(distinct_id).strip(),
                event=str(event_name).strip(),
                properties=properties,
            )
            return OutboxHandlerResult.ok(
                metadata={
                    "event": str(event_name),
                    "distinct_id": str(distinct_id),
                }
            )
        except Exception as exc:
            logger.exception("Unexpected error in TelemetryHandler")
            return OutboxHandlerResult.transient_failure(
                f"Telemetry capture error: {exc}",
                error_type=type(exc).__name__,
            )
