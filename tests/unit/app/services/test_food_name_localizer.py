from unittest.mock import AsyncMock

import pytest

from src.app.services.food_name_localizer import (
    is_ascii_display_name,
    needs_display_localization,
    translate_food_texts,
    translation_is_cacheable,
)
from src.domain.model.translation_result import TranslationOutcome, TranslationResult


@pytest.mark.asyncio
async def test_partial_result_is_renderable_but_not_cacheable():
    service = AsyncMock()
    service.translate_texts.return_value = TranslationResult(
        ("Cơm", "Rice"),
        TranslationOutcome.PARTIAL,
        "en",
        "vi",
    )

    result = await translate_food_texts(
        ["Rice", "Chicken"],
        target_language="vi",
        translation_service=service,
    )

    assert result.texts == ("Cơm", "Rice")
    assert not translation_is_cacheable(result)
    service.translate_texts.assert_awaited_once_with(["Rice", "Chicken"], "en", "vi")


@pytest.mark.asyncio
async def test_missing_service_returns_canonical_unavailable_result():
    result = await translate_food_texts(
        ["Rice"], target_language="vi", translation_service=None
    )

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.texts == ("Rice",)


@pytest.mark.asyncio
async def test_invalid_translation_service_result_is_unavailable():
    service = AsyncMock()
    service.translate_texts.return_value = ["Cơm"]

    result = await translate_food_texts(
        ["Rice"], target_language="vi", translation_service=service
    )

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.texts == ("Rice",)


def test_ascii_display_name_detects_english_leftovers():
    assert is_ascii_display_name("Rice vermicelli")
    assert is_ascii_display_name("Pork knuckle")
    assert is_ascii_display_name("Khoai tay")
    assert not is_ascii_display_name("Thịt bò")
    assert not is_ascii_display_name("Nước dùng Bún bò Huế")
    assert not is_ascii_display_name("  ")


def test_needs_display_localization_detects_english_food_phrases():
    assert needs_display_localization("Shredded pork skin and pork", "vi")
    assert needs_display_localization("Rice vermicelli", "vi")
    assert needs_display_localization("Pork knuckle", "vi")
    assert needs_display_localization("Chicken", "vi")
    assert needs_display_localization("Cilantro", "vi")
    assert needs_display_localization("Pork Pâté", "vi")
    assert needs_display_localization("Vietnamese Baguette", "vi")
    assert needs_display_localization("Bơ/mayo", "vi")
    assert not needs_display_localization("Khoai tay", "vi")
    assert not needs_display_localization("Thịt bò", "vi")
    assert not needs_display_localization("Thịt", "vi")
    assert not needs_display_localization("Dưa Leo Chua", "vi")
    assert not needs_display_localization("Cà Rốt Ngâm", "vi")
    assert not needs_display_localization("Sốt mayonnaise", "vi")
    assert not needs_display_localization("Shredded pork skin and pork", "en")
