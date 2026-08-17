"""Outcome-aware, presentation-only localization helpers for food names."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Protocol

from src.domain.model.translation_result import TranslationOutcome, TranslationResult


class FoodTextTranslationService(Protocol):
    """Minimal neutral translation contract used by read-path callers."""

    async def translate_texts(
        self,
        texts: Sequence[str],
        source_language: str,
        target_language: str,
    ) -> TranslationResult: ...


def _legacy_presentation_result(
    texts: Sequence[str],
    translated: Any,
    *,
    source_language: str,
    target_language: str,
) -> TranslationResult:
    """Render old list-shaped doubles without making them cacheable."""
    values = list(translated) if isinstance(translated, (list, tuple)) else []
    expanded = [
        value.strip() if isinstance(value, str) and value.strip() else original
        for original, value in zip(texts, values, strict=False)
    ]
    expanded.extend(texts[len(expanded) :])
    return TranslationResult(
        tuple(expanded),
        TranslationOutcome.PARTIAL,
        source_language,
        target_language,
    )


async def translate_food_texts(
    texts: Sequence[str],
    *,
    target_language: str,
    translation_service: Any | None,
    source_language: str = "en",
) -> TranslationResult:
    """Translate display text while preserving canonical fallback values.

    ``TranslationResult`` stays within the application layer. A narrow
    two-argument fallback is retained for older doubles while callers use the
    neutral three-argument API.
    """

    original = tuple(str(text) for text in texts)
    if not original or source_language == target_language:
        return TranslationResult.passthrough(
            original,
            source_language=source_language,
            target_language=target_language,
        )
    if translation_service is None:
        return TranslationResult.unavailable(
            original,
            source_language=source_language,
            target_language=target_language,
        )

    try:
        try:
            result = await translation_service.translate_texts(
                list(original), source_language, target_language
            )
        except TypeError:
            # Presentation-only compatibility for older test doubles. The
            # result is explicitly PARTIAL and therefore never cacheable.
            result = await translation_service.translate_texts(
                list(original), target_language
            )
            return _legacy_presentation_result(
                original,
                result,
                source_language=source_language,
                target_language=target_language,
            )
    except Exception:
        return TranslationResult.unavailable(
            original,
            source_language=source_language,
            target_language=target_language,
        )
    if isinstance(result, TranslationResult):
        values = tuple(result.texts)
        if len(values) == len(original):
            return result
        return TranslationResult(
            tuple(values[: len(original)]) + original[len(values) :],
            TranslationOutcome.PARTIAL,
            source_language,
            target_language,
        )
    return TranslationResult.unavailable(
        original,
        source_language=source_language,
        target_language=target_language,
    )


async def translate_for_presentation(
    translation_service: Any | None,
    texts: Sequence[str],
    target_language: str,
) -> TranslationResult:
    """Compatibility-named presentation wrapper used by catalog projections."""

    return await translate_food_texts(
        texts,
        target_language=target_language,
        translation_service=translation_service,
    )


def translated_values(
    originals: Sequence[str], result: TranslationResult
) -> tuple[str, ...]:
    """Return a response-safe tuple for any translation outcome."""

    return tuple(
        result.texts[index] if index < len(result.texts) else text
        for index, text in enumerate(originals)
    )


def is_ascii_display_name(name: str) -> bool:
    """True when a display name has no localized letters and still needs translation."""
    stripped = name.strip()
    return bool(stripped) and all(ord(character) < 128 for character in stripped)


_ENGLISH_CONNECTORS = re.compile(
    r"\b(and|with|of|the|in|from|style)\b", re.IGNORECASE
)
_ENGLISH_FOOD_HINTS = frozenset(
    {
        "beef",
        "bread",
        "broth",
        "chicken",
        "egg",
        "eggs",
        "fish",
        "fried",
        "grilled",
        "knuckle",
        "milk",
        "noodle",
        "noodles",
        "oil",
        "pork",
        "potato",
        "rice",
        "salad",
        "sauce",
        "shredded",
        "shrimp",
        "skin",
        "soup",
        "steamed",
        "vermicelli",
    }
)


def needs_display_localization(name: str, language: str) -> bool:
    """True when a leftover display name is still English for a non-English user."""
    if not language or language == "en":
        return False
    stripped = name.strip()
    if not is_ascii_display_name(stripped):
        return False
    tokens = re.findall(r"[A-Za-z]+", stripped.lower())
    if not tokens:
        return False
    if _ENGLISH_CONNECTORS.search(stripped):
        return True
    return any(token in _ENGLISH_FOOD_HINTS for token in tokens)


def translation_is_cacheable(result: TranslationResult) -> bool:
    """Only complete translations may enter locale-specific caches."""

    return result.outcome is TranslationOutcome.TRANSLATED
