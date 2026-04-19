"""Tests that food search caches partial localized results and skips the fallback."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.handlers.query_handlers.search_foods_query_handler import SearchFoodsQueryHandler
from src.app.queries.food.search_foods_query import SearchFoodsQuery


def _make_handler(localized_results=None, fallback_results=None):
    cache = MagicMock()
    cache.get_cached_search = AsyncMock(return_value=None)  # always cache miss
    cache.cache_search = AsyncMock()

    fat_secret = MagicMock()
    # First call: localized; second call: English fallback
    fat_secret.search_foods = AsyncMock(side_effect=[
        localized_results or [],
        fallback_results or [],
    ])

    mapping = MagicMock()
    mapping.map_search_item.side_effect = lambda x: x

    return SearchFoodsQueryHandler(
        cache_service=cache,
        mapping_service=mapping,
        fat_secret_service=fat_secret,
        translation_service=None,
    ), fat_secret, cache


@pytest.mark.asyncio
async def test_partial_localized_result_skips_fallback():
    """When localized search returns results (even partial), fallback must NOT run."""
    partial_results = [{"description": "Phở", "source": "fatsecret"}]
    handler, fat_secret, _ = _make_handler(localized_results=partial_results)

    query = SearchFoodsQuery(query="pho", language="vi", limit=10)
    await handler.handle(query)

    assert fat_secret.search_foods.call_count == 1, (
        f"Expected 1 FatSecret call (localized only), got {fat_secret.search_foods.call_count}"
    )


@pytest.mark.asyncio
async def test_partial_localized_result_is_cached():
    """Partial localized results must be cached immediately."""
    partial_results = [{"description": "Phở", "source": "fatsecret"}]
    handler, _, cache = _make_handler(localized_results=partial_results)

    query = SearchFoodsQuery(query="pho", language="vi", limit=10)
    await handler.handle(query)

    cache.cache_search.assert_called_once()
    call_args = cache.cache_search.call_args
    cached_data = call_args[0][1]  # second positional arg is the data
    assert cached_data == partial_results


@pytest.mark.asyncio
async def test_empty_localized_result_runs_fallback():
    """When localized search returns empty, the fallback path still runs."""
    fallback_results = [{"description": "Noodle soup", "source": "fatsecret"}]
    handler, fat_secret, _ = _make_handler(localized_results=[], fallback_results=fallback_results)

    query = SearchFoodsQuery(query="pho", language="vi", limit=10)
    await handler.handle(query)

    assert fat_secret.search_foods.call_count == 2
