"""Barcode translation regressions for canonical cache vs localized response."""

from unittest.mock import AsyncMock

import pytest
from tests.unit.handlers.query_handlers.test_lookup_barcode_query_handler_async import (
    _FoodReferenceRepo,
    _handler,
    _NeutralTranslator,
)

from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery


@pytest.mark.asyncio
async def test_non_english_first_scan_keeps_english_cache_for_later_english_read():
    """Vietnamese first-writer must not poison the global barcode cache."""
    repo = _FoodReferenceRepo()
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
