"""
Firebase Admin SDK service for push notifications.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


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
                        "No Firebase service account key found. Push notifications will be disabled."
                    )
            else:
                logger.info("Firebase Admin SDK already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise e

    def _get_service_account_key(self) -> Optional[Dict[str, Any]]:
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
                with open(service_account_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading Firebase service account file: {e}")
                return None

        return None

    def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: str,
        data: Optional[Dict[str, str]] = None,
        tokens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
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

    def _send_to_tokens(
        self, tokens: List[str], title: str, body: str, data: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send notification to specific FCM tokens."""
        try:
            # Ensure all data values are strings
            string_data = {k: str(v) for k, v in data.items()} if data else {}

            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=string_data,
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="high_priority_channel", sound="default"
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                            alert=messaging.ApsAlert(title=title, body=body),
                        )
                    )
                ),
            )

            # Send the message
            response = messaging.send_each_for_multicast(message)

            logger.info(
                f"Notification sent: {response.success_count} successful, {response.failure_count} failed"
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
        self, topic: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
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

            # Prepare message data
            message_data = data or {}
            message_data["topic"] = topic

            # Create message
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=message_data,
                topic=topic,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="high_priority_channel", sound="default"
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                            alert=messaging.ApsAlert(title=title, body=body),
                        )
                    )
                ),
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
