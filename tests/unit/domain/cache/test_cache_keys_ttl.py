from src.domain.cache.cache_keys import CacheKeys


def test_ttl_30_min_constant_exists():
    assert CacheKeys.TTL_30_MIN == 1800


def test_daily_breakdown_ttl_is_30_min():
    from datetime import date
    _, ttl = CacheKeys.daily_breakdown("user-1", date(2026, 1, 1))
    assert ttl == 1800, f"expected 1800, got {ttl}"


def test_weekly_budget_ttl_is_30_min():
    from datetime import date
    _, ttl = CacheKeys.weekly_budget("user-1", date(2026, 1, 1))
    assert ttl == 1800, f"expected 1800, got {ttl}"
