"""Unit tests for outbox exponential backoff service."""

from datetime import UTC, datetime

from src.domain.services.outbox_backoff_service import calculate_next_retry_at


def test_calculate_next_retry_at_exponential_growth():
    base_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Attempt 0: base * 2^0 = 5s + jitter [0, 2.5] -> between 5s and 7.5s
    t0 = calculate_next_retry_at(0, now=base_time)
    diff0 = (t0 - base_time).total_seconds()
    assert 5.0 <= diff0 <= 7.5

    # Attempt 1: base * 2^1 = 10s + jitter [0, 2.5] -> between 10s and 12.5s
    t1 = calculate_next_retry_at(1, now=base_time)
    diff1 = (t1 - base_time).total_seconds()
    assert 10.0 <= diff1 <= 12.5

    # Attempt 2: base * 2^2 = 20s + jitter [0, 2.5] -> between 20s and 22.5s
    t2 = calculate_next_retry_at(2, now=base_time)
    diff2 = (t2 - base_time).total_seconds()
    assert 20.0 <= diff2 <= 22.5

    # Attempt 3: base * 2^3 = 40s + jitter [0, 2.5] -> between 40s and 42.5s
    t3 = calculate_next_retry_at(3, now=base_time)
    diff3 = (t3 - base_time).total_seconds()
    assert 40.0 <= diff3 <= 42.5


def test_calculate_next_retry_at_caps_at_max_delay():
    base_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Large retry count capped at max_delay_seconds (default 3600s)
    t_large = calculate_next_retry_at(20, now=base_time, max_delay_seconds=3600.0)
    diff = (t_large - base_time).total_seconds()
    assert diff <= 3600.0


def test_calculate_next_retry_at_with_default_now():
    t = calculate_next_retry_at(1)
    assert t.tzinfo is not None
