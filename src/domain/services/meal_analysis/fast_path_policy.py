"""Configuration for meal image analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infra.config.settings import Settings


@dataclass(frozen=True)
class MealAnalyzeFastPathPolicy:
    """Configuration for meal image analysis."""

    max_attempts: int = 2
    max_output_tokens: int = 700

    @classmethod
    def from_settings(cls, settings: "Settings | None") -> "MealAnalyzeFastPathPolicy":
        """Build policy from settings, using sensible defaults."""
        if settings is None:
            return cls()

        return cls(
            max_attempts=getattr(settings, "MEAL_ANALYZE_MAX_ATTEMPTS", 2),
            max_output_tokens=getattr(settings, "MEAL_ANALYZE_MAX_OUTPUT_TOKENS", 700),
        )
