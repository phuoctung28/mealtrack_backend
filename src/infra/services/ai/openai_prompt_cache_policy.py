"""OpenAI prompt-cache request policy.

This module only builds provider-side prompt-cache request kwargs. It does not
cache responses and does not store raw prompts.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

_ALLOWED_RETENTION = {"in_memory", "24h"}
_SAFE_KEY_PART = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass(frozen=True)
class OpenAIPromptCachePolicy:
    """Build safe prompt-cache kwargs for OpenAI Responses API calls."""

    enabled: bool
    key_prefix: str = "mealtrack"
    retention: str | None = None

    def __post_init__(self) -> None:
        if self.retention and self.retention not in _ALLOWED_RETENTION:
            raise ValueError(
                "OPENAI_PROMPT_CACHE_RETENTION must be empty, 'in_memory', or '24h'"
            )

    def request_kwargs(
        self,
        *,
        model: str,
        purpose_hint: str | None,
        system_message: str | None,
    ) -> dict[str, Any]:
        """Return kwargs accepted by OpenAI Responses API methods."""
        if not self.enabled:
            return {}

        purpose = _safe_key_part(purpose_hint or "unknown")
        digest = hashlib.sha256(
            f"{model}\n{purpose}\n{system_message or ''}".encode()
        ).hexdigest()[:16]
        kwargs: dict[str, Any] = {
            "prompt_cache_key": f"{_safe_key_part(self.key_prefix)}:{purpose}:{digest}"
        }
        if self.retention:
            kwargs["prompt_cache_retention"] = self.retention
        return kwargs


def _safe_key_part(value: str) -> str:
    safe = _SAFE_KEY_PART.sub("-", value.strip()).strip("-").lower()
    return safe or "unknown"
