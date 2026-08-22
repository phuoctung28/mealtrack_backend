"""Transactional outbox handler for notification projection rescheduling."""

from __future__ import annotations

from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)


class NotificationRescheduleHandler(OutboxEventHandler):
    """Rebuild one user's notification rows outside the API process."""

    def __init__(self, service: DailyContextPrecomputeService | None = None) -> None:
        self._service = service or DailyContextPrecomputeService()

    async def handle(
        self,
        payload: dict[str, Any],
        context: OutboxEventContext,
    ) -> OutboxHandlerResult:
        user_id = payload.get("user_id") if isinstance(payload, dict) else None
        if not isinstance(user_id, str) or not user_id.strip():
            return OutboxHandlerResult.permanent_failure(
                "user_id must be a non-empty string",
                error_type="InvalidPayload",
            )
        try:
            count = await self._service.reschedule_user_notifications(user_id)
            return OutboxHandlerResult.ok(
                metadata={"user_id": user_id, "scheduled_count": count}
            )
        except Exception as exc:
            return OutboxHandlerResult.transient_failure(
                f"Notification reschedule failed: {exc}",
                error_type=type(exc).__name__,
            )
