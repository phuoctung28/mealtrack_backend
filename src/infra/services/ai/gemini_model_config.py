"""
Model configuration constants and data structures for Gemini model management.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GeminiModelPurpose(str, Enum):
    """Purpose-based model selection for rate limit distribution.

    Each purpose maps to a different Gemini model to distribute
    API calls across multiple rate limit pools (5-10 RPM each).
    """

    GENERAL = "general"  # Default, backward compatible
    MEAL_NAMES = "meal_names"  # High RPM (10/min) for fast name generation
    RECIPE = "recipe"  # Recipe generation (collapsed from PRIMARY + SECONDARY)
    BARCODE = "barcode"  # Barcode nutrition extraction (no thinking needed)


# Default cache settings
DEFAULT_MAX_CACHE_SIZE = 5  # Max number of model instances
DEFAULT_TTL_SECONDS = 3600  # 1 hour TTL for cached models
MEMORY_WARNING_THRESHOLD_MB = 400  # Warn when process exceeds this

# Model name defaults per purpose
PURPOSE_MODEL_DEFAULTS = {
    GeminiModelPurpose.GENERAL:    "gemini-2.5-flash",
    GeminiModelPurpose.MEAL_NAMES: "gemini-2.5-flash-lite",
    GeminiModelPurpose.RECIPE:     "gemini-2.5-flash-lite",  # Flash-Lite primary
    GeminiModelPurpose.BARCODE:    "gemini-2.5-flash-lite",
}

# Env var names per purpose
PURPOSE_ENV_VARS = {
    GeminiModelPurpose.GENERAL:    "GEMINI_MODEL",
    GeminiModelPurpose.MEAL_NAMES: "GEMINI_MODEL_NAMES",
    GeminiModelPurpose.RECIPE:     "GEMINI_MODEL_RECIPE",
    GeminiModelPurpose.BARCODE:    "GEMINI_MODEL",
}

# Default temperature per purpose
PURPOSE_TEMPERATURES: dict[GeminiModelPurpose, float] = {
    GeminiModelPurpose.GENERAL:    0.2,
    GeminiModelPurpose.MEAL_NAMES: 0.7,  # diversity is the point
    GeminiModelPurpose.RECIPE:     0.4,
    GeminiModelPurpose.BARCODE:    0.1,  # extraction — accuracy over creativity
}


@dataclass
class CachedModel:
    """Wrapper for cached model with metadata."""

    model: Any  # ChatGoogleGenerativeAI
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this cached model has expired."""
        return (time.time() - self.created_at) > ttl_seconds
