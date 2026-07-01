import logging
from unittest.mock import AsyncMock

import pytest

from src.app.handlers.query_handlers.lookup_barcode_query_handler import (
    LookupBarcodeQueryHandler,
)
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery


class _FoodReferenceRepo:
    def __init__(self):
        self.upserts = []

    async def get_by_barcode(self, _barcode: str):
        return None

    async def upsert(self, data):
        self.upserts.append(data)


class _Uow:
    def __init__(self, repo: _FoodReferenceRepo):
        self.food_references = repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def _handler(repo: _FoodReferenceRepo, **overrides):
    defaults = {
        "open_food_facts_service": AsyncMock(),
        "fat_secret_service": AsyncMock(),
        "async_uow_factory": lambda: _Uow(repo),
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
async def test_hit_log_uses_controlled_provider_source(caplog):
    raw_barcode = "036000291452"
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = {
        "barcode": raw_barcode,
        "name": "Rice",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
        "provider_source": raw_barcode,
    }
    handler = _handler(repo, fat_secret_service=fat_secret)

    with caplog.at_level(
        logging.INFO,
        logger="src.app.handlers.query_handlers.lookup_barcode_query_handler",
    ):
        result = await handler.handle(_query())

    assert result is not None
    assert raw_barcode not in caplog.text
    assert "provider_source=fatsecret" in caplog.text


@pytest.mark.asyncio
async def test_cache_warning_log_omits_result_barcode(caplog):
    raw_barcode = "036000291452"
    handler = _handler(_FoodReferenceRepo())

    with caplog.at_level(
        logging.WARNING,
        logger="src.app.handlers.query_handlers.lookup_barcode_query_handler",
    ):
        await handler._cache_result({"barcode": raw_barcode})

    assert "Skipping barcode cache: name is required" in caplog.text
    assert raw_barcode not in caplog.text
