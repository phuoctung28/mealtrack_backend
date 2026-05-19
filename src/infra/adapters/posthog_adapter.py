"""Small PostHog capture adapter for backend lifecycle events."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PostHogAdapter:
    """Fire-and-forget PostHog event capture using environment configuration."""

    def __init__(self) -> None:
        self.api_key = os.getenv("POSTHOG_API_KEY", "")
        self.host = os.getenv("POSTHOG_HOST", "https://app.posthog.com").rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def capture(
        self,
        *,
        distinct_id: str,
        event: str,
        properties: dict[str, Any],
    ) -> None:
        """Capture an event without blocking the caller on analytics failures."""
        if not self.enabled:
            return

        payload = {
            "api_key": self.api_key,
            "event": event,
            "distinct_id": distinct_id,
            "properties": properties,
        }
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(f"{self.host}/capture/", json=payload)
                response.raise_for_status()
        except Exception:
            logger.warning("PostHog capture failed for %s", event, exc_info=True)
