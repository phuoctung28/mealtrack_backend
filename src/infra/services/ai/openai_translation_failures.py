"""Sanitized translation provider failure classification."""

from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APITimeoutError, RateLimitError


@dataclass(frozen=True)
class TranslationFailure:
    category: str
    error_code: int | str | None = None


def classify_translation_failure(error: BaseException) -> TranslationFailure:
    """Map provider failures to bounded categories without retaining payloads."""
    if isinstance(error, (TimeoutError, APITimeoutError)):
        return TranslationFailure("timeout", "timeout")
    if isinstance(error, RateLimitError):
        return TranslationFailure("rate_limit", 429)
    if isinstance(error, APIConnectionError):
        return TranslationFailure("connection", "connection")
    name = type(error).__name__.lower()
    if "validation" in name or "schema" in name:
        return TranslationFailure("structural", "schema")
    return TranslationFailure("provider", None)
