"""Domain orchestration for bounded, outcome-aware text translation."""

from __future__ import annotations

from collections.abc import Sequence

from src.domain.constants.languages import (
    is_supported_translation_pair,
    normalize_language,
)
from src.domain.constants.translation_limits import translation_batch_within_limits
from src.domain.model.translation_result import TranslationOutcome, TranslationResult
from src.domain.ports.text_translation_port import TextTranslationPort


class TextTranslationService:
    """Validate translation requests and normalize provider outcomes."""

    def __init__(self, port: TextTranslationPort) -> None:
        self._port = port

    async def translate_texts(
        self,
        texts: Sequence[str],
        source_language: str | None,
        target_language: str | None,
    ) -> TranslationResult:
        original = tuple(str(text) for text in texts)
        source = normalize_language(source_language)
        target = normalize_language(target_language)
        if not original or source == target:
            return TranslationResult.passthrough(
                original, source_language=source, target_language=target
            )
        if not is_supported_translation_pair(
            source, target
        ) or not translation_batch_within_limits(list(original)):
            return TranslationResult.unavailable(
                original, source_language=source, target_language=target
            )

        # Empty fields (for example an optional recipe description) are data,
        # not translation requests. Keep their positions while excluding them
        # from the provider payload so a model cannot invent content for them.
        unique = list(dict.fromkeys(text for text in original if text))
        if not unique:
            return TranslationResult.passthrough(
                original, source_language=source, target_language=target
            )
        try:
            provider_result = await self._port.translate_texts(
                unique, source_language=source, target_language=target
            )
        except Exception:
            return TranslationResult.unavailable(
                original, source_language=source, target_language=target
            )

        provider_texts = tuple(provider_result.items)
        expanded: list[str] = []
        status = provider_result.outcome
        index_map = {text: index for index, text in enumerate(unique)}
        for text in original:
            if not text:
                expanded.append(text)
                continue
            index = index_map[text]
            if index < len(provider_texts) and provider_texts[index]:
                expanded.append(provider_texts[index])
            else:
                expanded.append(text)
                status = TranslationOutcome.PARTIAL
        if len(provider_texts) != len(unique):
            status = TranslationOutcome.PARTIAL
        return TranslationResult(tuple(expanded), status, source, target)
