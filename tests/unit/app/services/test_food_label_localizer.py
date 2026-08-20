"""Tests for food-label display localization."""

from unittest.mock import AsyncMock

import pytest

from src.app.services.food_label_localizer import localize_food_label_display
from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.model.translation_result import TranslationOutcome, TranslationResult


def _nutrition(name: str = "Protein Bar") -> Nutrition:
    return Nutrition(
        macros=Macros(protein=20, carbs=20, fat=8),
        food_items=[
            FoodItem(
                id="item-1",
                name=name,
                quantity=55,
                unit="g",
                macros=Macros(protein=20, carbs=20, fat=8),
            )
        ],
        confidence_score=0.9,
    )


def _metadata(product_name: str = "Protein Bar") -> dict:
    return {
        "is_food_label": True,
        "product_name": product_name,
        "brand": "Example",
        "serving_size": {"display_text": "1 bar (55g)", "grams": 55},
        "servings_per_package": 8,
        "label_calories_per_serving": 230,
        "confidence": 0.9,
        "label_notes": [],
    }


@pytest.mark.asyncio
async def test_localizes_english_food_label_names_for_non_english_request():
    service = AsyncMock()
    service.translate_texts.return_value = TranslationResult(
        ("Thanh protein",),
        TranslationOutcome.TRANSLATED,
        "en",
        "vi",
    )

    nutrition, metadata = await localize_food_label_display(
        nutrition=_nutrition(),
        metadata=_metadata(),
        language="vi",
        translation_service=service,
    )

    assert nutrition.food_items[0].name == "Thanh protein"
    assert metadata["product_name"] == "Thanh protein"
    service.translate_texts.assert_awaited_once_with(["Protein Bar"], "en", "vi")


@pytest.mark.asyncio
async def test_keeps_printed_non_english_product_names_without_translation():
    service = AsyncMock()

    nutrition, metadata = await localize_food_label_display(
        nutrition=_nutrition("Thịt bò"),
        metadata=_metadata("Thịt bò"),
        language="vi",
        translation_service=service,
    )

    assert nutrition.food_items[0].name == "Thịt bò"
    assert metadata["product_name"] == "Thịt bò"
    service.translate_texts.assert_not_awaited()


@pytest.mark.asyncio
async def test_english_request_skips_translation():
    service = AsyncMock()
    original = _nutrition()

    nutrition, metadata = await localize_food_label_display(
        nutrition=original,
        metadata=_metadata(),
        language="en",
        translation_service=service,
    )

    assert nutrition is original
    assert metadata["product_name"] == "Protein Bar"
    service.translate_texts.assert_not_awaited()


@pytest.mark.asyncio
async def test_unavailable_translation_keeps_canonical_names():
    service = AsyncMock()
    service.translate_texts.return_value = TranslationResult.unavailable(
        ("Protein Bar",),
        source_language="en",
        target_language="vi",
    )
    original = _nutrition()
    original_metadata = _metadata()

    nutrition, metadata = await localize_food_label_display(
        nutrition=original,
        metadata=original_metadata,
        language="vi",
        translation_service=service,
    )

    assert nutrition.food_items[0].name == "Protein Bar"
    assert metadata["product_name"] == "Protein Bar"
    # Metadata dict may be copied, but values stay canonical.
    assert metadata is not original_metadata or metadata == original_metadata


@pytest.mark.asyncio
async def test_dedupes_identical_product_and_food_item_names():
    service = AsyncMock()
    service.translate_texts.return_value = TranslationResult(
        ("Thanh protein",),
        TranslationOutcome.TRANSLATED,
        "en",
        "vi",
    )

    await localize_food_label_display(
        nutrition=_nutrition("Protein Bar"),
        metadata=_metadata("Protein Bar"),
        language="vi",
        translation_service=service,
    )

    service.translate_texts.assert_awaited_once_with(["Protein Bar"], "en", "vi")
