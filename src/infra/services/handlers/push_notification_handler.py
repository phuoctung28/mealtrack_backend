"""Push notification outbox event handler wrapping FirebaseService."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxEventHandler,
    OutboxHandlerResult,
)
from src.infra.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


class PushNotificationHandler(OutboxEventHandler):
    """Dispatches push notifications via Firebase Admin SDK."""

    def __init__(self, firebase_service: FirebaseService | None = None) -> None:
        self._firebase_service = firebase_service or FirebaseService()

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

        title = payload.get("title")
        body = payload.get("body")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(body, str)
            or not body.strip()
        ):
            return OutboxHandlerResult.permanent_failure(
                "Notification title and body must be non-empty strings",
                error_type="ValidationError",
            )

        notification_type = payload.get("notification_type", "scheduled")
        data = payload.get("data")

        try:
            # 1. Topic broadcast
            if "topic" in payload:
                topic = str(payload["topic"]).strip()
                if not topic:
                    return OutboxHandlerResult.permanent_failure(
                        "Topic cannot be empty",
                        error_type="ValidationError",
                    )
                res = self._firebase_service.send_to_topic(
                    topic=topic,
                    title=title,
                    body=body,
                    data=data,
                )
                if res.get("success"):
                    return OutboxHandlerResult.ok(
                        metadata={"message_id": res.get("message_id")}
                    )
                if res.get("reason") == "firebase_not_initialized":
                    return OutboxHandlerResult.transient_failure(
                        "Firebase Admin SDK not initialized",
                        error_type="FirebaseNotInitialized",
                    )
                return OutboxHandlerResult.transient_failure(
                    res.get("error", "Failed to send topic notification"),
                    error_type="TopicSendError",
                )

            # 2. Token multicast
            if "tokens" in payload:
                tokens = payload["tokens"]
                if not isinstance(tokens, list) or len(tokens) == 0:
                    return OutboxHandlerResult.permanent_failure(
                        "Tokens must be a non-empty list",
                        error_type="ValidationError",
                    )
                res = self._firebase_service.send_multicast(
                    tokens=tokens,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    data=data,
                )
                if res.get("success"):
                    if res.get("sent", 0) > 0:
                        return OutboxHandlerResult.ok(
                            metadata={"sent": res["sent"], "failed": res["failed"]}
                        )
                    return OutboxHandlerResult.transient_failure(
                        f"All {res.get('failed', 0)} token deliveries failed",
                        error_type="FCMDeliveryFailure",
                        metadata={"failed_tokens": res.get("failed_tokens")},
                    )
                if res.get("reason") == "firebase_not_initialized":
                    return OutboxHandlerResult.transient_failure(
                        "Firebase Admin SDK not initialized",
                        error_type="FirebaseNotInitialized",
                    )
                return OutboxHandlerResult.transient_failure(
                    res.get("error", "FCM multicast send error"),
                    error_type="MulticastError",
                )

            # 3. Direct user notification
            if "user_id" in payload:
                user_id = str(payload["user_id"]).strip()
                if not user_id:
                    return OutboxHandlerResult.permanent_failure(
                        "user_id cannot be empty",
                        error_type="ValidationError",
                    )
                res = self._firebase_service.send_notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    data=data,
                )
                if res.get("success"):
                    return OutboxHandlerResult.ok(metadata=res)
                if res.get("reason") == "no_tokens":
                    return OutboxHandlerResult.permanent_failure(
                        "User has no registered FCM tokens",
                        error_type="NoTokensForUser",
                    )
                if res.get("reason") == "firebase_not_initialized":
                    return OutboxHandlerResult.transient_failure(
                        "Firebase Admin SDK not initialized",
                        error_type="FirebaseNotInitialized",
                    )
                return OutboxHandlerResult.transient_failure(
                    res.get("error", "FCM notification send error"),
                    error_type="FCMSendError",
                )

            return OutboxHandlerResult.permanent_failure(
                "Push notification payload must contain 'tokens', 'topic', or 'user_id'",
                error_type="ValidationError",
            )

        except ValueError as exc:
            return OutboxHandlerResult.permanent_failure(
                str(exc),
                error_type="ValidationError",
            )
        except Exception as exc:
            logger.exception("Unexpected error in PushNotificationHandler")
            return OutboxHandlerResult.transient_failure(
                f"Unexpected error: {exc}",
                error_type=type(exc).__name__,
            )
