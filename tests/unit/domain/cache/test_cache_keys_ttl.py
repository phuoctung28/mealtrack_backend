from src.domain.cache.cache_keys import CacheKeys


def test_ttl_30_min_constant_exists():
    assert CacheKeys.TTL_30_MIN == 1800
