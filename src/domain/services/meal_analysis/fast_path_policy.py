"""Fast-path policy for meal image analysis.

Centralizes timeouts and retry limits for the meal image fast path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infra.config.settings import Settings


@dataclass(frozen=True)
class MealAnalyzeFastPathPolicy:
    """Configuration holder for meal image fast-path analysis."""

    primary_timeout_seconds: float = 2.5
    retry_timeout_seconds: float = 1.5
    max_attempts: int = 2
    max_output_tokens: int = 700
    translation_in_critical_path: bool = False
    runtime_policy_enabled: bool = True
    canary_percent: int = 100

    @classmethod
    def legacy(cls) -> "MealAnalyzeFastPathPolicy":
        """Return compatibility defaults used before fast-path rollout."""
        return cls(
            primary_timeout_seconds=10.0,
            retry_timeout_seconds=10.0,
            max_attempts=1,
            max_output_tokens=1024,
            translation_in_critical_path=True,
            runtime_policy_enabled=False,
            canary_percent=0,
        )

    @classmethod
    def from_settings(
        cls, settings: "Settings | None"
    ) -> "MealAnalyzeFastPathPolicy":
        """Build policy values from application settings."""
        if settings is None:
            return cls()

        if not settings.MEAL_ANALYZE_RUNTIME_POLICY_ENABLED:
            legacy = cls.legacy()
            return cls(
                primary_timeout_seconds=legacy.primary_timeout_seconds,
                retry_timeout_seconds=legacy.retry_timeout_seconds,
                max_attempts=legacy.max_attempts,
                max_output_tokens=legacy.max_output_tokens,
                translation_in_critical_path=legacy.translation_in_critical_path,
                runtime_policy_enabled=False,
                canary_percent=settings.MEAL_ANALYZE_CANARY_PERCENT,
            )

        return cls(
            primary_timeout_seconds=settings.MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS,
            retry_timeout_seconds=settings.MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS,
            max_attempts=settings.MEAL_ANALYZE_MAX_ATTEMPTS,
            max_output_tokens=settings.MEAL_ANALYZE_MAX_OUTPUT_TOKENS,
            translation_in_critical_path=settings.MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH,
            runtime_policy_enabled=settings.MEAL_ANALYZE_RUNTIME_POLICY_ENABLED,
            canary_percent=settings.MEAL_ANALYZE_CANARY_PERCENT,
        )

    def should_use_fast_path(self, user_id: str) -> bool:
        """Determine if this user should be in the fast-path canary cohort."""
        if not self.runtime_policy_enabled:
            return False
        if self.canary_percent <= 0:
            return False
        if self.canary_percent >= 100:
            return True
        bucket = int(hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16) % 100
        return bucket < self.canary_percent
