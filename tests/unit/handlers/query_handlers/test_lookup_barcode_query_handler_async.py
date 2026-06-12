from unittest.mock import AsyncMock

import pytest

from src.app.handlers.query_handlers.lookup_barcode_query_handler import (
    LookupBarcodeQueryHandler,
)
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery


class _FoodReferenceRepo:
    def __init__(self, cached=None):
        self.cached = cached
        self.upserts = []

    async def get_by_barcode(self, barcode: str):
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

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="en"))

    assert result is not None
    assert result["source"] == "fatsecret"
    assert repo.upserts == [result]
