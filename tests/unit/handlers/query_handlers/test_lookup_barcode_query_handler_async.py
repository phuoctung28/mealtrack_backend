from unittest.mock import AsyncMock, Mock

import pytest

from src.app.handlers.query_handlers.lookup_barcode_query_handler import (
    LookupBarcodeQueryHandler,
)
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery


class _FoodReferenceRepo:
    def __init__(self, cached=None):
        self.cached = cached
        self.lookups = []
        self.upserts = []

    async def get_by_barcode(self, barcode: str):
        self.lookups.append(barcode)
        if isinstance(self.cached, dict) and barcode in self.cached:
            return self.cached[barcode]
        return self.cached

    async def upsert(self, data):
        self.upserts.append(data)


class _Uow:
    def __init__(self, repo: _FoodReferenceRepo):
        self.food_references = repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class _UowFactory:
    def __init__(self, repo: _FoodReferenceRepo):
        self.repo = repo
        self.created = 0

    def __call__(self):
        self.created += 1
        return _Uow(self.repo)


def _handler(repo: _FoodReferenceRepo, **overrides):
    defaults = {
        "open_food_facts_service": AsyncMock(),
        "fat_secret_service": AsyncMock(),
        "async_uow_factory": _UowFactory(repo),
    }
    defaults.update(overrides)
    return LookupBarcodeQueryHandler(**defaults)


def _query():
    return LookupBarcodeQuery(
        barcode="00036000291452",
        scanned_barcode="036000291452",
        aliases=("036000291452", "0036000291452", "00036000291452"),
        language="en",
    )


@pytest.mark.asyncio
async def test_lookup_barcode_returns_cached_product_from_async_uow():
    repo = _FoodReferenceRepo(
        {
            "barcode": "123",
            "name": "Rice",
            "protein_100g": 2.7,
            "carbs_100g": 28,
            "fat_100g": 0.3,
        }
    )
    fat_secret = AsyncMock()
    handler = _handler(repo, fat_secret_service=fat_secret)

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="en"))

    assert result is not None
    assert result["source"] == "cache"
    fat_secret.get_product.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_barcode_caches_fatsecret_hit_with_async_uow():
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = {
        "barcode": "123",
        "name": "Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(repo, fat_secret_service=fat_secret)

    result = await handler.handle(_query())

    assert result is not None
    assert result["source"] == "fatsecret"
    assert repo.upserts[0]["barcode"] == "00036000291452"
    assert result["barcode"] == "036000291452"


@pytest.mark.asyncio
async def test_lookup_barcode_skips_untrusted_brave_cache_row():
    repo = _FoodReferenceRepo(
        {
            "00036000291452": {
                "barcode": "00036000291452",
                "name": "Old Brave",
                "protein_100g": 1,
                "carbs_100g": 2,
                "fat_100g": 3,
                "source": "brave_search",
                "is_verified": False,
            }
        }
    )
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = []
    off = AsyncMock()
    off.get_product.return_value = None
    handler = _handler(repo, fat_secret_service=fat_secret, open_food_facts_service=off)

    result = await handler.handle(_query())

    assert result is None
    assert fat_secret.get_product.await_count == 3


@pytest.mark.asyncio
async def test_lookup_barcode_uses_fdc_exact_hit_and_caches_verified():
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    off = AsyncMock()
    off.get_product.return_value = None
    food_data = AsyncMock()
    food_data.get_branded_food_by_gtin.return_value = {
        "fdcId": 2,
        "description": "Test Cereal",
        "gtinUpc": "036000291452",
        "foodNutrients": [
            {"nutrientId": 1003, "value": 8},
            {"nutrientId": 1005, "value": 72},
            {"nutrientId": 1004, "value": 2.5},
        ],
    }
    mapping = Mock()
    mapping.map_fdc_barcode_product.return_value = {
        "name": "Test Cereal",
        "barcode": "00036000291452",
        "protein_100g": 8,
        "carbs_100g": 72,
        "fat_100g": 2.5,
        "source": "usda_fdc",
        "is_verified": True,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        food_data_service=food_data,
        food_mapping_service=mapping,
    )

    result = await handler.handle(_query())

    assert result is not None
    assert result["source"] == "usda_fdc"
    assert result["barcode"] == "036000291452"
    assert repo.upserts[0]["barcode"] == "00036000291452"
    assert repo.upserts[0]["is_verified"] is True


@pytest.mark.asyncio
async def test_lookup_barcode_fdc_error_falls_through_to_brave_estimate():
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    fat_secret.search_foods.return_value = []
    off = AsyncMock()
    off.get_product.return_value = None
    food_data = AsyncMock()
    food_data.get_branded_food_by_gtin.side_effect = RuntimeError("fdc down")
    brave = AsyncMock()
    brave.get_product.return_value = {
        "name": "Maybe Cereal",
        "protein_100g": 1,
        "carbs_100g": 2,
        "fat_100g": 0,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        food_data_service=food_data,
        food_mapping_service=AsyncMock(),
        brave_search_service=brave,
    )

    result = await handler.handle(_query())

    assert result is not None
    assert result["source"] == "brave_search"
    assert result["is_estimate"] is True
    assert repo.upserts == []
