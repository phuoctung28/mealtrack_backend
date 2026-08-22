"""Transactional outbox handler for Firebase account cleanup."""

from __future__ import annotations

import asyncio
from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.services.firebase_auth_service import FirebaseAuthService


class FirebaseAccountCleanupHandler(OutboxEventHandler):
    """Revoke sessions and delete Firebase auth after SQL deletion commits."""

    def __init__(self, service: FirebaseAuthService | None = None) -> None:
        self._service = service or FirebaseAuthService()

    async def handle(
        self,
        payload: dict[str, Any],
        context: OutboxEventContext,
    ) -> OutboxHandlerResult:
        firebase_uid = (
            payload.get("firebase_uid") if isinstance(payload, dict) else None
        )
        if not isinstance(firebase_uid, str) or not firebase_uid.strip():
            return OutboxHandlerResult.permanent_failure(
                "firebase_uid must be a non-empty string",
                error_type="InvalidPayload",
            )

        try:
            revoked = await asyncio.to_thread(
                self._service.revoke_refresh_tokens, firebase_uid
            )
            if not revoked:
                return OutboxHandlerResult.transient_failure(
                    "Firebase refresh-token revocation failed",
                    error_type="FirebaseTokenRevocationError",
                )
            deleted = await asyncio.to_thread(
                self._service.delete_firebase_user, firebase_uid
            )
            if not deleted:
                return OutboxHandlerResult.transient_failure(
                    "Firebase account deletion returned false",
                    error_type="FirebaseDeletionError",
                )
            return OutboxHandlerResult.ok(
                metadata={"firebase_uid": firebase_uid, "event_id": context.event_id}
            )
        except Exception as exc:
            return OutboxHandlerResult.transient_failure(
                f"Firebase account cleanup failed: {exc}",
                error_type=type(exc).__name__,
            )
