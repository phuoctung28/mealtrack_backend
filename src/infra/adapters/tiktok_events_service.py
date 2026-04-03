"""
TikTok Events API service for server-side ad attribution tracking.

Sends conversion events (purchase, etc.) to TikTok for ad campaign optimization.
Fire-and-forget: never raises, logs errors silently.
"""
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TIKTOK_EVENTS_API_URL = "https://business-api.tiktok.com/open_api/v1.3/event/track/"


class TikTokEventsService:
    """Server-side TikTok Events API client."""

    def __init__(self, access_token: str, app_id: str):
        self._access_token = access_token
        self._app_id = app_id
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Content-Type": "application/json",
                "Access-Token": access_token,
            },
        )

    @staticmethod
    def _hash_pii(value: str) -> str:
        """SHA256 hash for PII (email, external_id) per TikTok spec."""
        return hashlib.sha256(value.lower().strip().encode()).hexdigest()

    async def track_event(
        self,
        event: str,
        event_id: str,
        user_email: str = "",
        external_id: str = "",
        properties: Optional[dict] = None,
    ) -> None:
        """Send event to TikTok Events API. Never raises."""
        try:
            user_data = {}
            if user_email:
                user_data["em"] = self._hash_pii(user_email)
            if external_id:
                user_data["external_id"] = self._hash_pii(external_id)

            payload = {
                "pixel_code": self._app_id,
                "data": [
                    {
                        "event": event,
                        "event_id": event_id,
                        "event_source": "app",
                        "event_source_id": self._app_id,
                        "timestamp": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%S%z"
                        ),
                        "user_data": user_data,
                        "properties": properties or {},
                    }
                ],
            }

            response = await self._client.post(
                TIKTOK_EVENTS_API_URL, json=payload
            )

            if response.status_code == 200:
                logger.info(f"TikTok event sent: {event} (id={event_id})")
            else:
                logger.warning(
                    f"TikTok event failed: {event} — "
                    f"status={response.status_code}, body={response.text}"
                )
        except Exception as e:
            logger.warning(f"TikTok event error: {event} — {e}")

    async def track_complete_payment(
        self,
        event_id: str,
        user_email: str,
        firebase_uid: str,
        value: float,
        currency: str,
    ) -> None:
        """Send CompletePayment event for subscription purchase."""
        await self.track_event(
            event="CompletePayment",
            event_id=event_id,
            user_email=user_email,
            external_id=firebase_uid,
            properties={
                "value": value,
                "currency": currency,
                "content_type": "product",
                "content_name": "Nutree AI Subscription",
            },
        )


# Singleton instance
_instance: Optional[TikTokEventsService] = None


def get_tiktok_events_service() -> Optional[TikTokEventsService]:
    """Get singleton TikTok Events service. Returns None if not configured."""
    global _instance
    if _instance is not None:
        return _instance

    access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    app_id = os.getenv("TIKTOK_APP_ID", "")

    if not access_token or not app_id:
        return None

    _instance = TikTokEventsService(access_token, app_id)
    return _instance
