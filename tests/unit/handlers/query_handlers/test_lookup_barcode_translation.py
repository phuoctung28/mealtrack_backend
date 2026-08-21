"""Barcode translation regressions for canonical cache vs localized response."""

from unittest.mock import AsyncMock

import pytest
from tests.unit.handlers.query_handlers.test_lookup_barcode_query_handler_async import (
    _estimated_cached_reference,
    _FoodReferenceRepo,
    _handler,
    _NeutralTranslator,
)

from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery


@pytest.mark.asyncio
async def test_non_english_first_scan_keeps_english_cache_for_later_english_read():
    """Vietnamese first-writer must not poison the global barcode cache."""
    repo = _FoodReferenceRepo(
        cached_after_upsert={
            "id": 17,
            "barcode": "123",
            "name": "Brown Rice",
            "protein_100g": 2.7,
            "carbs_100g": 28,
            "fat_100g": 0.3,
            "source": "fatsecret",
            "is_verified": True,
        }
    )
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = {
        "barcode": "123",
        "name": "Brown Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        translation_service=_NeutralTranslator(),
    )

    vietnamese = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))
    assert vietnamese["name"] == "Cơm gạo lứt"
    assert repo.upserts[0]["name"] == "Brown Rice"

    # Simulate cache hit from the English canonical upsert.
    repo.cached = {
        "123": {
            "id": 17,
            "barcode": "123",
            "name": "Brown Rice",
            "protein_100g": 2.7,
            "carbs_100g": 28,
            "fat_100g": 0.3,
            "source": "fatsecret",
            "is_verified": True,
        }
    }
    english_handler = _handler(repo, fat_secret_service=AsyncMock())
    english = await english_handler.handle(
        LookupBarcodeQuery(barcode="123", language="en")
    )

    assert english["name"] == "Brown Rice"
    assert english["source"] == "cache"


@pytest.mark.asyncio
async def test_cached_fatsecret_hit_localizes_for_vietnamese_request():
    repo = _FoodReferenceRepo(
        {
            "123": {
                "id": 17,
                "barcode": "123",
                "name": "Brown Rice",
                "protein_100g": 2.7,
                "carbs_100g": 28,
                "fat_100g": 0.3,
                "source": "fatsecret",
                "is_verified": True,
            }
        }
    )
    handler = _handler(repo, translation_service=_NeutralTranslator())

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["source"] == "cache"
    assert result["name"] == "Cơm gạo lứt"


@pytest.mark.asyncio
async def test_cached_unknown_source_english_name_still_localizes():
    repo = _FoodReferenceRepo(
        {
            "123": {
                "id": 17,
                "barcode": "123",
                "name": "Brown Rice",
                "protein_100g": 2.7,
                "carbs_100g": 28,
                "fat_100g": 0.3,
            }
        }
    )
    handler = _handler(repo, translation_service=_NeutralTranslator())

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["name"] == "Cơm gạo lứt"


@pytest.mark.asyncio
async def test_brave_estimate_localizes_materialized_reference():
    repo = _FoodReferenceRepo(cached_after_upsert=_estimated_cached_reference())
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = []
    off = AsyncMock()
    off.get_product.return_value = None
    brave = AsyncMock()
    brave.get_product.return_value = {
        "name": "Brown Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        brave_search_service=brave,
        translation_service=_NeutralTranslator(),
    )

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["source"] == "brave_search"
    assert result["name"] == "Cơm gạo lứt"
    assert result["is_estimate"] is True
    assert result["origin"] == "local"


@pytest.mark.asyncio
async def test_materialized_localized_brave_estimate_skips_translation():
    repo = _FoodReferenceRepo(
        cached_after_upsert=_estimated_cached_reference("Cơm gạo lứt")
    )
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = []
    off = AsyncMock()
    off.get_product.return_value = None
    brave = AsyncMock()
    brave.get_product.return_value = {
        "name": "Cơm gạo lứt",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    translator = AsyncMock()
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        brave_search_service=brave,
        translation_service=translator,
    )

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["name"] == "Cơm gạo lứt"
    translator.translate_texts.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_estimate_localizes_materialized_reference():
    repo = _FoodReferenceRepo(cached_after_upsert=_estimated_cached_reference())
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = []
    off = AsyncMock()
    off.get_product.return_value = None
    meal_gen = AsyncMock()
    meal_gen.generate_meal_plan_async.return_value = {
        "is_food": True,
        "name": "Brown Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        meal_generation_service=meal_gen,
        translation_service=_NeutralTranslator(),
    )

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["source"] == "ai_estimate"
    assert result["name"] == "Cơm gạo lứt"
    assert result["is_estimate"] is True
    assert result["origin"] == "local"
    assert result["food_reference_id"] == 74


@pytest.mark.asyncio
async def test_fatsecret_name_estimate_localizes_materialized_reference():
    repo = _FoodReferenceRepo(cached_after_upsert=_estimated_cached_reference())
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = [
        {
            "name": "Some FS Match",
            "protein_100g": 2.7,
            "carbs_100g": 28,
            "fat_100g": 0.3,
        }
    ]
    off = AsyncMock()
    off.get_product.return_value = None
    brave = AsyncMock()
    brave.get_product.return_value = {
        "name": "Brown Rice",
        "protein_100g": None,
        "carbs_100g": None,
        "fat_100g": None,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        brave_search_service=brave,
        translation_service=_NeutralTranslator(),
    )

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["source"] == "fatsecret_name_search"
    assert result["name"] == "Cơm gạo lứt"
    assert result["origin"] == "local"
    assert result["food_reference_id"] == 74
