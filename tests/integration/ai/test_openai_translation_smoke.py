"""Credential-gated smoke test for the OpenAI translation path."""

from __future__ import annotations

import os

import pytest

from src.domain.constants.languages import normalize_language
from src.domain.model.translation_result import TranslationOutcome
from src.domain.services.translation.text_translation_service import (
    TextTranslationService,
)
from src.infra.adapters.openai_translation_adapter import OpenAITranslationAdapter
from src.infra.config.settings import settings
from src.infra.services.ai.providers.openai_provider import OpenAIProvider


@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY is required for the live translation smoke test",
)
async def test_openai_translation_smoke_preserves_placeholder() -> None:
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        request_timeout_seconds=max(
            1, int(settings.OPENAI_TRANSLATION_TIMEOUT_SECONDS)
        ),
        max_retries=settings.OPENAI_MAX_RETRIES,
        store_responses=False,
        prompt_cache_enabled=False,
    )
    service = TextTranslationService(
        OpenAITranslationAdapter(
            provider=provider,
            model=settings.OPENAI_TRANSLATION_MODEL,
        )
    )

    result = await service.translate_texts(
        ["Add {amount} ml of sauce."],
        normalize_language("en"),
        normalize_language("vi"),
    )

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items and "{amount}" in result.items[0]


@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY is required for the live translation smoke test",
)
async def test_openai_translation_smoke_handles_vietnamese_meals() -> None:
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        request_timeout_seconds=max(
            1, int(settings.OPENAI_TRANSLATION_TIMEOUT_SECONDS)
        ),
        max_retries=settings.OPENAI_MAX_RETRIES,
        store_responses=False,
        prompt_cache_enabled=False,
    )
    service = TextTranslationService(
        OpenAITranslationAdapter(
            provider=provider,
            model=settings.OPENAI_TRANSLATION_MODEL,
        )
    )

    result = await service.translate_texts(
        [
            "Broken rice with grilled pork, pork skin, and a fried egg.",
            "Beef pho with rice noodles and fresh herbs.",
            "Grilled pork banh mi with pickled carrots.",
        ],
        normalize_language("en"),
        normalize_language("vi"),
    )

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert len(result.items) == 3
    translated = [item.casefold() for item in result.items]
    assert "cơm tấm" in translated[0]
    assert "phở bò" in translated[1]
    assert "bánh mì" in translated[2]
