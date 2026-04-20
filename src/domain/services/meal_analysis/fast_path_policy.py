"""Fast-path policy for meal image analysis.

Centralizes timeouts and retry limits for the meal image fast path.
"""

from __future__ import annotations

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

    @classmethod
    def from_settings(
        cls, settings: "Settings | None"
    ) -> "MealAnalyzeFastPathPolicy":
        """Build policy values from application settings."""
        if settings is None:
            return cls()

        return cls(
            primary_timeout_seconds=settings.MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS,
            retry_timeout_seconds=settings.MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS,
            max_attempts=settings.MEAL_ANALYZE_MAX_ATTEMPTS,
            max_output_tokens=settings.MEAL_ANALYZE_MAX_OUTPUT_TOKENS,
            translation_in_critical_path=settings.MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH,
        )
