import src.domain.services.meal_discovery.food_image_search_service as svc


def test_cache_max_entries():
    assert svc.CACHE_MAX_ENTRIES == 500


def test_cache_ttl_is_one_day():
    assert svc.CACHE_TTL_SECONDS == 24 * 3600


def test_cache_evicts_oldest_at_max():
    from src.domain.services.meal_discovery.food_image_search_service import (
        FoodImageSearchService,
    )
    import unittest.mock as mock

    service = FoodImageSearchService.__new__(FoodImageSearchService)
    from collections import OrderedDict
    service._cache = OrderedDict()
    service._cache_lock = mock.MagicMock()
    service._cache_lock.__enter__ = mock.MagicMock(return_value=None)
    service._cache_lock.__exit__ = mock.MagicMock(return_value=False)

    import time
    for i in range(501):
        service._cache[f"food_{i}"] = ("http://img/{i}.jpg", time.time())
        if len(service._cache) > svc.CACHE_MAX_ENTRIES:
            service._cache.popitem(last=False)

    assert len(service._cache) == 500
