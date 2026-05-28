import src.domain.services.meal_discovery.food_image_search_service as svc


def test_cache_max_entries():
    assert svc.CACHE_MAX_ENTRIES == 500


def test_cache_ttl_is_one_day():
    assert svc.CACHE_TTL_SECONDS == 24 * 3600


def test_cache_evicts_oldest_at_max():
    from src.domain.services.meal_discovery.food_image_search_service import (
        FoodImageSearchService,
    )
    from collections import OrderedDict

    service = FoodImageSearchService.__new__(FoodImageSearchService)
    service._cache = OrderedDict()

    import time
    for i in range(501):
        service._cache[f"food_{i}"] = ("http://img/{i}.jpg", time.time())
        if len(service._cache) > svc.CACHE_MAX_ENTRIES:
            service._cache.popitem(last=False)

    assert len(service._cache) == 500
