"""Tests for provider-neutral translation orchestration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.model.translation_result import TranslationOutcome, TranslationResult
from src.domain.services.translation.text_translation_service import (
    TextTranslationService,
)


@pytest.fixture
def port():
    adapter = MagicMock()
    adapter.translate_texts = AsyncMock()
    return adapter


@pytest.fixture
def service(port):
    return TextTranslationService(port)


@pytest.mark.asyncio
async def test_translates_and_expands_deduplicated_texts(service, port):
    port.translate_texts.return_value = TranslationResult(
        ("Poulet", "Riz"), TranslationOutcome.TRANSLATED, "en", "fr"
    )

    result = await service.translate_texts(
        ["Chicken", "Rice", "Chicken"], "en", "fr"
    )

    assert result.items == ("Poulet", "Riz", "Poulet")
    assert result.outcome is TranslationOutcome.TRANSLATED
    port.translate_texts.assert_awaited_once_with(
        ["Chicken", "Rice"], source_language="en", target_language="fr"
    )


@pytest.mark.asyncio
async def test_same_language_is_passthrough(service, port):
    result = await service.translate_texts(["Chicken"], "en", "en")

    assert result.items == ("Chicken",)
    assert result.outcome is TranslationOutcome.PASSTHROUGH
    port.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_empty_items_are_not_sent_to_provider(service, port):
    port.translate_texts.return_value = TranslationResult(
        ("Poulet",), TranslationOutcome.TRANSLATED, "en", "fr"
    )

    result = await service.translate_texts(["Chicken", "", "Chicken"], "en", "fr")

    assert result.items == ("Poulet", "", "Poulet")
    assert result.outcome is TranslationOutcome.TRANSLATED
    port.translate_texts.assert_awaited_once_with(
        ["Chicken"], source_language="en", target_language="fr"
    )


@pytest.mark.asyncio
async def test_all_empty_items_bypass_provider(service, port):
    result = await service.translate_texts(["", ""], "en", "fr")

    assert result.items == ("", "")
    assert result.outcome is TranslationOutcome.PASSTHROUGH
    port.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_unsupported_pair_is_unavailable(service, port):
    result = await service.translate_texts(["Chicken"], "en", "ko")

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.items == ("Chicken",)
    port.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_provider_failure_is_unavailable_and_canonical(service, port):
    port.translate_texts.side_effect = RuntimeError("provider unavailable")

    result = await service.translate_texts(["Chicken"], "en", "vi")

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.items == ("Chicken",)


@pytest.mark.asyncio
async def test_partial_provider_result_fills_missing_canonical_text(service, port):
    port.translate_texts.return_value = TranslationResult(
        ("Gà",), TranslationOutcome.PARTIAL, "en", "vi"
    )

    result = await service.translate_texts(["Chicken", "Rice"], "en", "vi")

    assert result.items == ("Gà", "Rice")
    assert result.outcome is TranslationOutcome.PARTIAL
    assert result.cacheable is False
