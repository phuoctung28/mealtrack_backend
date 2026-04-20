"""Port for notification de-duplication storage.

Domain services must not depend on infra/database directly. This port provides
an atomic 'claim' primitive so multiple API workers don't send duplicates.
"""

from __future__ import annotations

from typing import Protocol


class NotificationDedupPort(Protocol):
    def try_claim_sent(self, *, user_id: str, notification_type: str, minute_key: str) -> bool:
        """Return True if already claimed by another worker, else claim and return False."""

    def cleanup_old_sent_logs(self, *, older_than_hours: int) -> int:
        """Delete rows older than N hours. Returns deleted row count (best effort)."""

