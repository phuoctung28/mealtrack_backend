"""
Firebase Admin SDK service for push notifications.

FCM contract: messages carry title/body in `data` for mobile handlers, plus
`aps.alert` for iOS native display.
"""

import json
import logging
import os
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

from src.infra.services.push.android_payload_builder import build_android_config
from src.infra.services.push.apns_payload_builder import build_apns_config

logger = logging.getLogger(__name__)


def _validate_display_text(title: str | None, body: str | None) -> tuple[str, str]:
    """Return stripped display text or fail before sending a bad notification."""
    display_title = title.strip() if isinstance(title, str) else ""
    display_body = body.strip() if isinstance(body, str) else ""
    if not display_title or not display_body:
        raise ValueError("Notification title and body must be non-empty")
    return display_title, display_body


class FirebaseService:
    """Service for Firebase Admin SDK operations."""

    def __init__(self):
        """Initialize Firebase Admin SDK."""
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Get service account key from environment
                service_account_key = self._get_service_account_key()

                if service_account_key:
                    # Initialize with service account key
                    cred = credentials.Certificate(service_account_key)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin SDK initialized successfully")
                else:
                    logger.warning(
                        "No Firebase service account key found. "
                        "Push notifications will be disabled."
                    )
            else:
                logger.info("Firebase Admin SDK already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise e

    def _get_service_account_key(self) -> dict[str, Any] | None:
        """Get Firebase service account key from environment variables."""
        # Try to get from JSON string in environment variable
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                return json.loads(service_account_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
                return None

        # Try to get from file path
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if service_account_path and os.path.exists(service_account_path):
            try:
                with open(service_account_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error reading Firebase service account file: {e}")
                return None

        return None

    def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: str,
        data: dict[str, str] | None = None,
        tokens: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Send push notification to user's devices.

        Args:
            user_id: User ID (for logging purposes)
            title: Notification title
            body: Notification body
            notification_type: Type of notification
            data: Optional data payload
            tokens: List of FCM tokens (if not provided, will need to be fetched)

        Returns:
            Dictionary with success status and results
        """
        try:
            # Check if Firebase is initialized
            if firebase_admin._apps:
                # Prepare message data
                message_data = data or {}
                message_data["type"] = notification_type
                message_data["user_id"] = user_id

                if tokens:
                    # Send to specific tokens
                    return self._send_to_tokens(tokens, title, body, message_data)
                else:
                    logger.warning(f"No FCM tokens provided for user {user_id}")
                    return {"success": False, "reason": "no_tokens"}
            else:
                logger.warning(
                    "Firebase Admin SDK not initialized. Cannot send notification."
                )
                return {"success": False, "reason": "firebase_not_initialized"}

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}

    def send_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        notification_type: str = "scheduled",
        data: dict[str, str] | None = None,
    ) -> dict:
        """Send the same notification to a batch of FCM tokens (up to 500 per call)."""
        if not firebase_admin._apps:
            return {"success": False, "reason": "firebase_not_initialized"}

        message_data = dict(data or {})
        message_data["type"] = notification_type
        return self._send_to_tokens(tokens, title, body, message_data)

    def _send_to_tokens(
        self, tokens: list[str], title: str, body: str, data: dict[str, str]
    ) -> dict[str, Any]:
        """Send notification to specific FCM tokens.

        Title/body are injected into `data` for mobile handlers and mirrored
        into APNs alert fields for iOS background notifications.
        """
        try:
            display_title, display_body = _validate_display_text(title, body)

            # Ensure all data values are strings; inject title/body for mobile.
            string_data = {k: str(v) for k, v in data.items()} if data else {}
            string_data["title"] = display_title
            string_data["body"] = display_body

            # Create multicast message with no top-level notification field.
            message = messaging.MulticastMessage(
                data=string_data,
                tokens=tokens,
                android=build_android_config(),
                apns=build_apns_config(title=display_title, body=display_body),
            )

            # Send the message
            response = messaging.send_each_for_multicast(message)

            logger.info(
                "Notification sent: %s successful, %s failed",
                response.success_count,
                response.failure_count,
            )

            # Handle failed tokens
            failed_tokens = []
            if response.failure_count > 0:
                for idx, result in enumerate(response.responses):
                    if not result.success:
                        error_code = "unknown_error"
                        if result.exception:
                            # Extract error code from exception
                            error_code = getattr(result.exception, "code", None)
                            if error_code is None:
                                error_code = type(result.exception).__name__

                        failed_tokens.append(
                            {"token": tokens[idx], "error": error_code}
                        )
                        logger.warning(f"Failed to send to token {idx}: {error_code}")

            return {
                "success": True,
                "sent": response.success_count,
                "failed": response.failure_count,
                "failed_tokens": failed_tokens,
            }

        except Exception as e:
            logger.error(f"Error sending multicast message: {e}")
            return {"success": False, "reason": "send_error", "error": str(e)}

    def send_to_topic(
        self, topic: str, title: str, body: str, data: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """
        Send notification to a topic.

        Args:
            topic: Firebase topic name
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Dictionary with success status and results
        """
        try:
            if not firebase_admin._apps:
                return {"success": False, "reason": "firebase_not_initialized"}

            display_title, display_body = _validate_display_text(title, body)

            # Prepare data payload for mobile handlers.
            message_data = {k: str(v) for k, v in (data or {}).items()}
            message_data["topic"] = topic
            message_data["title"] = display_title
            message_data["body"] = display_body

            # Create message (no top-level notification field)
            message = messaging.Message(
                data=message_data,
                topic=topic,
                android=build_android_config(),
                apns=build_apns_config(title=display_title, body=display_body),
            )

            # Send the message
            response = messaging.send(message)

            logger.info(f"Topic notification sent successfully: {response}")

            return {"success": True, "message_id": response}

        except Exception as e:
            logger.error(f"Error sending topic notification: {e}")
            return {"success": False, "reason": "send_error", "error": str(e)}

    def is_initialized(self) -> bool:
        """Check if Firebase Admin SDK is initialized."""
        return len(firebase_admin._apps) > 0
