"""Controlled rollout gate for catalog meal recommendations."""

from __future__ import annotations

import hashlib
import hmac


class MealRecommendationCohortService:
    """Fail-closed server-side gate with optional allowlist and HMAC cohorts."""

    def __init__(
        self,
        *,
        enabled: bool,
        internal_user_ids: str = "",
        cohort_percent: int = 0,
        cohort_salt: str = "",
    ) -> None:
        self.enabled = enabled
        self.internal_user_ids = _parse_csv(internal_user_ids)
        self.cohort_percent = max(0, min(100, cohort_percent))
        self.cohort_salt = cohort_salt

    def is_enabled_for_user(self, user_id: str) -> bool:
        if not self.enabled:
            return False
        if user_id in self.internal_user_ids:
            return True
        if self.cohort_percent <= 0:
            return False
        if not self.cohort_salt:
            return False
        return _bucket(user_id, self.cohort_salt) < self.cohort_percent


def _parse_csv(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def _bucket(user_id: str, salt: str) -> int:
    digest = hmac.new(
        salt.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return int(digest[:8], 16) % 100
