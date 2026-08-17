"""Neutral port for provider-backed text translation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.domain.model.translation_result import TranslationResult


class TextTranslationPort(ABC):
    """Infrastructure contract for translating an ordered text batch."""

    @abstractmethod
    async def translate_texts(
        self,
        texts: Sequence[str],
        *,
        source_language: str,
        target_language: str,
    ) -> TranslationResult:
        """Translate texts while preserving order and returning an outcome."""
