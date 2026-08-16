"""Sanitized metadata envelope for structured OpenAI responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OpenAIStructuredGenerationResult:
    parsed: Any
    raw_message: Any = None
    refusal: bool = False
    incomplete: bool = False
    usage: dict[str, int] = field(default_factory=dict)
