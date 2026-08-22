"""Registry for pluggable outbox event handlers."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)

logger = logging.getLogger(__name__)


class _DefaultUnregisteredHandler:
    """Fallback handler for unregistered event types, failing permanently to move to DLQ."""

    async def handle(
        self,
        payload: dict[str, Any],
        context: OutboxEventContext,
    ) -> OutboxHandlerResult:
        logger.warning(
            "No outbox handler registered for event_type='%s' (outbox_id=%s, event_id=%s). "
            "Failing permanently to DLQ.",
            context.event_type,
            context.outbox_id,
            context.event_id,
        )
        return OutboxHandlerResult.permanent_failure(
            f"No handler registered for event type '{context.event_type}'",
            error_type="UnregisteredEventType",
            metadata={"unregistered_event_type": context.event_type},
        )


class OutboxHandlerRegistry:
    """Central registry mapping outbox event types to event handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, OutboxEventHandler] = {}
        self._fallback_handler: OutboxEventHandler = _DefaultUnregisteredHandler()

    def register(self, event_type: str, handler: OutboxEventHandler) -> None:
        """Register a handler for a specific event type."""
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if not hasattr(handler, "handle"):
            raise TypeError("Handler must implement OutboxEventHandler protocol")
        self._handlers[event_type] = handler
        logger.debug("Registered outbox handler for event_type='%s'", event_type)

    def unregister(self, event_type: str) -> None:
        """Unregister a handler for an event type if present."""
        self._handlers.pop(event_type, None)

    def get(self, event_type: str) -> OutboxEventHandler | None:
        """Retrieve the registered handler for an event type, or None if not found."""
        return self._handlers.get(event_type)

    def get_or_fallback(self, event_type: str) -> OutboxEventHandler:
        """Retrieve the registered handler or the default fallback handler."""
        return self._handlers.get(event_type, self._fallback_handler)

    def has(self, event_type: str) -> bool:
        """Check whether an event type has a registered handler."""
        return event_type in self._handlers

    @property
    def registered_event_types(self) -> list[str]:
        """List all currently registered event types."""
        return list(self._handlers.keys())
