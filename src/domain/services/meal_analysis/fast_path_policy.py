"""Configuration for meal image analysis."""

from __future__ import annotations

from dataclasses import dataclass

MEAL_ANALYZE_DEFAULT_MAX_OUTPUT_TOKENS = 8192


@dataclass(frozen=True)
class MealAnalyzeFastPathPolicy:
    """Configuration for meal image analysis."""

    max_attempts: int = 2
    max_output_tokens: int = MEAL_ANALYZE_DEFAULT_MAX_OUTPUT_TOKENS

    @classmethod
    def from_settings(cls, settings: object | None) -> "MealAnalyzeFastPathPolicy":
        """Build policy from a settings-like object, using sensible defaults."""
        if settings is None:
            return cls()

        return cls(
            max_attempts=getattr(settings, "MEAL_ANALYZE_MAX_ATTEMPTS", 2),
            max_output_tokens=getattr(
                settings,
                "MEAL_ANALYZE_MAX_OUTPUT_TOKENS",
                MEAL_ANALYZE_DEFAULT_MAX_OUTPUT_TOKENS,
            ),
        )
