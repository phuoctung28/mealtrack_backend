"""
Tests for timing instrumentation in CreateManualMealCommandHandler.
Verifies that handler awaits cache invalidation (not fire-and-forget) and
that timing log messages are emitted.
"""

import asyncio
import logging
import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.create_manual_meal_command import (
    CreateManualMealCommand,
    CustomNutrition,
    ManualMealItem,
)
from src.app.handlers.command_handlers.create_manual_meal_command_handler import (
    CreateManualMealCommandHandler,
)
from src.app.services.cache_invalidation_service import CacheInvalidationService


# ---------------------------------------------------------------------------
# Minimal fakes (no mocking framework dependency for simple objects)
# ---------------------------------------------------------------------------


class _FakeMeals:
    def __init__(self, fake_meal):
        self._meal = fake_meal

    async def save(self, meal):
        return self._meal


class _FakeUsers:
    async def find_by_id(self, user_id):
        return None


class _FakeUow:
    def __init__(self, fake_meal):
        self.meals = _FakeMeals(fake_meal)
        self.users = _FakeUsers()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_meal():
    m = MagicMock()
    m.meal_id = "test-meal-id"
    m.created_at = None
    return m


_UUID_1 = "550e8400-e29b-41d4-a716-446655440001"
_UUID_2 = "550e8400-e29b-41d4-a716-446655440002"


def _make_command(user_id: str = _UUID_1) -> CreateManualMealCommand:
    return CreateManualMealCommand(
        user_id=user_id,
        items=[
            ManualMealItem(
                fdc_id=None,
                name="Rice",
                quantity=100.0,
                unit="g",
                custom_nutrition=CustomNutrition(
                    calories_per_100g=130.0,
                    protein_per_100g=2.7,
                    carbs_per_100g=28.0,
                    fat_per_100g=0.3,
                ),
            )
        ],
        dish_name="Rice Bowl",
        meal_type="lunch",
        target_date=None,
        source="manual",
        emoji=None,
    )


# ---------------------------------------------------------------------------
# Test A: slow cache delay is visible in elapsed time (handler awaits it)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_timing_logs_show_cache_delay(caplog):
    """Handler must await cache invalidation; a slow cache inflates elapsed time."""
    DELAY_S = 0.05  # 50 ms per operation

    slow_cache = MagicMock()

    async def slow_invalidate(key):
        await asyncio.sleep(DELAY_S)

    async def slow_invalidate_pattern(pattern):
        await asyncio.sleep(DELAY_S)

    slow_cache.invalidate = slow_invalidate
    slow_cache.invalidate_pattern = slow_invalidate_pattern

    cache_svc = CacheInvalidationService(cache=slow_cache)
    fake_meal = _make_meal()
    handler = CreateManualMealCommandHandler(
        uow=_FakeUow(fake_meal),
        cache_invalidation=cache_svc,
    )

    cmd = _make_command()

    t_start = time.perf_counter()
    with caplog.at_level(logging.INFO):
        result = await handler.handle(cmd)
    elapsed = time.perf_counter() - t_start

    # If handler awaits cache, elapsed must be ≥ one slow operation delay
    assert elapsed >= DELAY_S, (
        f"Handler returned in {elapsed * 1000:.0f}ms — expected ≥{DELAY_S * 1000:.0f}ms. "
        "Cache invalidation may not be awaited."
    )

    timing_logs = [r.message for r in caplog.records if "manual_save handler timing" in r.message]
    assert timing_logs, "No 'manual_save handler timing' log found — instrumentation missing."

    # Result is the saved meal
    assert result is fake_meal


# ---------------------------------------------------------------------------
# Test B: fast (no-op) cache emits timing log without bloating elapsed time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_timing_logs_fast_cache(caplog):
    """Fast (no-op) cache completes quickly and still emits a timing log."""
    fast_cache = MagicMock()
    fast_cache.invalidate = AsyncMock()
    fast_cache.invalidate_pattern = AsyncMock()
    cache_svc = CacheInvalidationService(cache=fast_cache)

    fake_meal = _make_meal()
    handler = CreateManualMealCommandHandler(
        uow=_FakeUow(fake_meal),
        cache_invalidation=cache_svc,
    )

    cmd = _make_command(user_id=_UUID_2)

    with caplog.at_level(logging.INFO):
        result = await handler.handle(cmd)

    timing_logs = [r.message for r in caplog.records if "manual_save handler timing" in r.message]
    assert timing_logs, "No 'manual_save handler timing' log found — instrumentation missing."

    assert result is fake_meal


# ---------------------------------------------------------------------------
# Test C: cache_invalidation_service emits per-family timing log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_invalidation_service_emits_timing_log(caplog):
    """after_meal_write emits a cache_invalidation timing log with critical/secondary/total."""
    fast_cache = MagicMock()
    fast_cache.invalidate = AsyncMock()
    fast_cache.invalidate_pattern = AsyncMock()
    svc = CacheInvalidationService(cache=fast_cache)

    with caplog.at_level(logging.INFO):
        await svc.after_meal_write("550e8400-e29b-41d4-a716-446655440003", date(2026, 6, 10))

    timing_logs = [r.message for r in caplog.records if "cache_invalidation timing" in r.message]
    assert timing_logs, "No 'cache_invalidation timing' log found in CacheInvalidationService."
    assert "critical_ms" in timing_logs[0]
    assert "secondary_ms" in timing_logs[0]
    assert "total_ms" in timing_logs[0]
