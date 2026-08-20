from unittest.mock import AsyncMock, Mock

import pytest

from src.app.handlers.query_handlers.lookup_barcode_query_handler import (
    LookupBarcodeQueryHandler,
)
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.domain.model.translation_result import TranslationOutcome, TranslationResult
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService


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


class _NeutralTranslator:
    async def translate_texts(self, texts, source_language, target_language):
        assert source_language == "en"
        assert target_language == "vi"
        return TranslationResult(
            ("Cơm gạo lứt",), TranslationOutcome.TRANSLATED, "en", "vi"
        )


@pytest.mark.asyncio
async def test_lookup_barcode_returns_cached_product_from_async_uow():
    repo = _FoodReferenceRepo(
        {
            "id": 42,
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
    assert result["origin"] == "local"
    assert result["food_reference_id"] == 42
    fat_secret.get_product.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_barcode_caches_fatsecret_hit_with_async_uow():
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = {
        "barcode": "123",
        "name": "Rice",
        "origin": "provider",
        "source_namespace": "fatsecret",
        "source_food_id": "50953",
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
    assert result["origin"] == "provider"
    assert result["source_namespace"] == "fatsecret"
    assert result["source_food_id"] == "50953"


@pytest.mark.asyncio
async def test_non_english_barcode_fetches_and_stores_english_then_localizes_response():
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

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    fat_secret.get_product.assert_awaited_once_with("123", region="US", language="en")
    assert repo.upserts[0]["name"] == "Brown Rice"
    assert result["name"] == "Cơm gạo lứt"


@pytest.mark.asyncio
async def test_non_english_openfoodfacts_english_name_is_localized_without_persisting_metadata():
    repo = _FoodReferenceRepo()
    fat_secret = AsyncMock()
    fat_secret.get_product.return_value = None
    off = AsyncMock()
    off.get_product.return_value = OpenFoodFactsService()._map_product(
        {
            "product_name": "Riz brun",
            "product_name_en": "Brown Rice",
            "nutriments": {
                "proteins_100g": 2.7,
                "carbohydrates_100g": 28,
                "fat_100g": 0.3,
            },
        }
    )
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
        translation_service=_NeutralTranslator(),
    )

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["name"] == "Cơm gạo lứt"
    assert "source_language" not in repo.upserts[0]


@pytest.mark.asyncio
async def test_lookup_barcode_uses_openfoodfacts_when_fatsecret_is_unavailable():
    repo = _FoodReferenceRepo()
    fat_secret = None
    off = AsyncMock()
    off.get_product.return_value = {
        "name": "Brown Rice",
        "barcode": "0036000291452",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(
        repo,
        fat_secret_service=fat_secret,
        open_food_facts_service=off,
    )

    result = await handler.handle(_query())

    assert result is not None
    assert result["source"] == "openfoodfacts"
    assert result["name"] == "Brown Rice"


@pytest.mark.asyncio
async def test_lookup_barcode_rejects_openfoodfacts_result_without_name():
    repo = _FoodReferenceRepo()
    off = AsyncMock()
    off.get_product.return_value = {
        "name": None,
        "barcode": "0036000291452",
        "protein_100g": 2.7,
        "carbs_100g": 28,
        "fat_100g": 0.3,
    }
    handler = _handler(
        repo,
        fat_secret_service=None,
        open_food_facts_service=off,
    )

    result = await handler.handle(_query())

    assert result is None
    assert repo.upserts == []


@pytest.mark.asyncio
async def test_cached_barcode_uses_reference_identity_without_provider_metadata():
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
    translator = AsyncMock()
    handler = _handler(repo, translation_service=translator)

    result = await handler.handle(LookupBarcodeQuery(barcode="123", language="vi"))

    assert result["name"] == "Brown Rice"
    assert result["origin"] == "local"
    assert result["food_reference_id"] == 17
    translator.translate_texts.assert_not_awaited()


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
async def test_lookup_barcode_uses_fdc_exact_hit_caches_verified_and_localizes():
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
        translation_service=_NeutralTranslator(),
    )

    base_query = _query()
    result = await handler.handle(
        LookupBarcodeQuery(
            barcode=base_query.barcode,
            scanned_barcode=base_query.scanned_barcode,
            aliases=base_query.aliases,
            language="vi",
        )
    )

    assert result is not None
    assert result["source"] == "usda_fdc"
    assert result["barcode"] == "036000291452"
    assert result["name"] == "Cơm gạo lứt"
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
