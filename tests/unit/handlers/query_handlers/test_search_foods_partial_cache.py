"""Tests that food search caches partial localized results and skips the fallback."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.handlers.query_handlers.search_foods_query_handler import (
    SearchFoodsQueryHandler,
)
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.ports.food_reference_repository_port import (
    FoodReferenceSearchProjection,
)
from src.observability import (
    reset_observability_connector_for_test,
    set_observability_connector_for_test,
)


class _Metrics:
    def __init__(self):
        self.calls = []

    def initialize(self):
        return None

    def capture_exception(self, error, *, context=None):
        return None

    def capture_message(self, message, *, level="info", context=None):
        return None

    def log_event(self, level, message, *, attributes=None):
        return None

    def increment_metric(self, name, value=1.0, *, unit=None, attributes=None):
        self.calls.append(("increment", name, value, unit, attributes))

    def gauge_metric(self, name, value, *, unit=None, attributes=None):
        self.calls.append(("gauge", name, value, unit, attributes))

    def distribution_metric(self, name, value, *, unit=None, attributes=None):
        self.calls.append(("distribution", name, value, unit, attributes))

    def set_request_context(self, *, request_id, method, path, user_id=None):
        return None

    def start_span(self, *, operation, description=None, context=None):
        from contextlib import nullcontext

        return nullcontext()

    def flush(self, *, timeout=5):
        return None


def teardown_function():
    reset_observability_connector_for_test()


def _local_rice() -> FoodReferenceSearchProjection:
    return FoodReferenceSearchProjection(
        id=7,
        name="Rice",
        name_normalized="rice",
        brand=None,
        source="catalog_seed",
        is_verified=True,
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        allowed_units=[{"unit": "g", "gram_weight": 1.0, "description": "1 g"}],
    )


def _make_handler(localized_results=None, fallback_results=None, local_results=None):
    cache = MagicMock()
    cache.get_cached_search = AsyncMock(return_value=None)  # always cache miss
    cache.cache_search = AsyncMock()

    fat_secret = MagicMock()
    # First call: localized; second call: English fallback
    fat_secret.search_foods = AsyncMock(
        side_effect=[
            localized_results or [],
            fallback_results or [],
        ]
    )

    mapping = MagicMock()
    mapping.map_search_item.side_effect = lambda x: x

    local_search = AsyncMock(return_value=local_results or [])

    return (
        SearchFoodsQueryHandler(
            cache_service=cache,
            mapping_service=mapping,
            fat_secret_service=fat_secret,
            translation_service=None,
            local_search=local_search,
        ),
        fat_secret,
        cache,
        local_search,
    )


@pytest.mark.asyncio
async def test_partial_localized_result_skips_fallback():
    """When localized search returns results (even partial), fallback must NOT run."""
    partial_results = [{"description": "Phở", "source": "fatsecret"}]
    handler, fat_secret, _, _ = _make_handler(localized_results=partial_results)

    query = SearchFoodsQuery(query="pho", language="vi", limit=10)
    await handler.handle(query)

    assert (
        fat_secret.search_foods.call_count == 1
    ), f"Expected 1 fatsecret call (localized only), got {fat_secret.search_foods.call_count}"


@pytest.mark.asyncio
async def test_partial_localized_result_is_cached():
    """Partial localized results must be cached immediately."""
    partial_results = [{"description": "Phở", "source": "fatsecret"}]
    handler, _, cache, _ = _make_handler(localized_results=partial_results)

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
    handler, fat_secret, _, _ = _make_handler(
        localized_results=[], fallback_results=fallback_results
    )

    query = SearchFoodsQuery(query="pho", language="vi", limit=10)
    await handler.handle(query)

    assert fat_secret.search_foods.call_count == 2


@pytest.mark.asyncio
async def test_english_search_calls_fatsecret_when_local_is_empty():
    """Manual food search should use FatSecret on cache miss after local misses."""
    handler, fat_secret, cache, local_search = _make_handler(
        localized_results=[{"description": "Chicken breast", "source": "fatsecret"}]
    )

    query = SearchFoodsQuery(query="chicken", language="en", limit=7)
    result = await handler.handle(query)

    cache.get_cached_search.assert_awaited_once_with("chicken")
    local_search.assert_awaited_once_with("chicken", "US", 7)
    fat_secret.search_foods.assert_awaited_once_with("chicken", max_results=7)
    assert result["results"][0]["source"] == "fatsecret"


@pytest.mark.asyncio
async def test_search_returns_local_results_without_provider_call():
    handler, fat_secret, _, local_search = _make_handler(local_results=[_local_rice()])

    result = await handler.handle(SearchFoodsQuery(query="rice", language="en", limit=1))

    local_search.assert_awaited_once_with("rice", "US", 1)
    fat_secret.search_foods.assert_not_awaited()
    assert result["results"][0]["source"] == "food_reference"
    assert result["results"][0]["food_reference_id"] == 7


@pytest.mark.asyncio
async def test_search_metrics_are_bounded_and_do_not_include_query_text():
    metrics = _Metrics()
    set_observability_connector_for_test(metrics)
    handler, _, _, _ = _make_handler(local_results=[_local_rice()])

    await handler.handle(SearchFoodsQuery(query="secret rice query", language="en", limit=1))

    assert (
        "distribution",
        "food_search.operation.latency_ms",
    ) == metrics.calls[0][:2]
    assert (
        "increment",
        "food_search.requests",
    ) == metrics.calls[1][:2]
    attributes = metrics.calls[1][4]
    assert attributes == {
        "operation": "search",
        "source": "local",
        "language": "en",
        "status": "success",
    }
    assert "secret rice query" not in str(metrics.calls)


@pytest.mark.asyncio
async def test_provider_outage_returns_partial_local_results():
    handler, fat_secret, _, _ = _make_handler(local_results=[_local_rice()])
    fat_secret.search_foods = AsyncMock(side_effect=Exception("provider unavailable"))

    result = await handler.handle(SearchFoodsQuery(query="rice", language="en", limit=5))

    assert result["results"] == [
        handler.mapping_service.map_search_item(
            handler._local_projection_to_raw(_local_rice())
        )
    ]


@pytest.mark.asyncio
async def test_cache_outage_degrades_to_local_and_provider_results():
    handler, fat_secret, cache, local_search = _make_handler(
        localized_results=[{"description": "Rice cakes", "source": "fatsecret"}],
        local_results=[_local_rice()],
    )
    cache.get_cached_search = AsyncMock(side_effect=Exception("redis unavailable"))
    cache.cache_search = AsyncMock(side_effect=Exception("redis unavailable"))

    result = await handler.handle(SearchFoodsQuery(query="rice", language="en", limit=5))

    cache.get_cached_search.assert_awaited_once_with("rice")
    local_search.assert_awaited_once_with("rice", "US", 5)
    fat_secret.search_foods.assert_awaited_once_with("rice", max_results=4)
    assert [item["source"] for item in result["results"]] == [
        "food_reference",
        "fatsecret",
    ]


@pytest.mark.asyncio
async def test_provider_duplicate_does_not_replace_verified_local_result():
    handler, fat_secret, _, _ = _make_handler(
        localized_results=[
            {
                "description": "Rice",
                "name_normalized": "rice",
                "source": "fatsecret",
            }
        ],
        local_results=[_local_rice()],
    )

    result = await handler.handle(SearchFoodsQuery(query="rice", language="en", limit=5))

    fat_secret.search_foods.assert_awaited_once_with("rice", max_results=4)
    assert len(result["results"]) == 1
    assert result["results"][0]["source"] == "food_reference"


@pytest.mark.asyncio
async def test_cached_search_respects_requested_limit():
    cache = MagicMock()
    cache.get_cached_search = AsyncMock(
        return_value=[
            {"description": "Rice", "source": "fatsecret"},
            {"description": "Rice noodles", "source": "fatsecret"},
        ]
    )
    cache.cache_search = AsyncMock()
    fat_secret = MagicMock()
    fat_secret.search_foods = AsyncMock()
    mapping = MagicMock()
    mapping.map_search_item.side_effect = lambda x: x
    handler = SearchFoodsQueryHandler(
        cache_service=cache,
        mapping_service=mapping,
        fat_secret_service=fat_secret,
    )

    result = await handler.handle(
        SearchFoodsQuery(query="rice", language="en", limit=1, autocomplete=True)
    )

    assert len(result["results"]) == 1
    fat_secret.search_foods.assert_not_awaited()
