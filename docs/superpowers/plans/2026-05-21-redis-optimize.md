# Redis Command Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Upstash Redis commands from >620K/month to <200K/month by eliminating the Redis hash notification pipeline and replacing the Redis auth cache with a process-level TTLCache.

**Architecture:** Option A removes all Redis HSET/EXPIRE/HGETALL/EXISTS from the notification system by (a) adding an FCM eligibility filter to the precompute SQL query, (b) replacing the Redis sentinel with an in-memory Python set, and (c) fetching real-time `calories_consumed` from PostgreSQL at send-time instead of Redis. Option B replaces the Redis GET/SET for auth UID lookups with a `cachetools.TTLCache` in `auth_cache.py`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, redis.asyncio, cachetools 5.3+

---

## File Map

| File | Change |
|---|---|
| `requirements.txt` | Add `cachetools>=5.3.0` |
| `src/domain/cache/cache_keys.py` | Add `TTL_30_MIN = 1800`; change `daily_breakdown` → `TTL_30_MIN`, `weekly_budget` → `TTL_30_MIN` |
| `src/infra/cache/redis_client.py` | Replace `KEYS` with `scan_iter` in `delete_pattern` |
| `src/api/dependencies/auth_cache.py` | Replace Redis GET/SET/DEL with `TTLCache` |
| `src/infra/services/daily_context_precompute_service.py` | Add FCM filter to Query 1; replace Redis sentinel with module-level set; remove Redis hash build; change return type to `int`; remove `redis_client` from constructor |
| `src/infra/services/scheduled_notification_service.py` | Add `_fetch_calories_consumed_batch`; replace `hgetall_batch` call; update `DailyContextPrecomputeService()` constructor |
| `tests/unit/infra/test_daily_context_precompute_service.py` | Update tests for new sentinel + constructor |
| `tests/unit/infra/test_scheduled_notification_service.py` | Update `test_send_loop_marks_notifications_sent` |
| `tests/unit/api/dependencies/test_auth_cache.py` | New test file |

---

## Task 1: Add cachetools dependency + TTL_30_MIN constant

**Files:**
- Modify: `requirements.txt`
- Modify: `src/domain/cache/cache_keys.py:13-14`

- [ ] **Step 1: Write a failing test for TTL_30_MIN**

```python
# tests/unit/domain/cache/test_cache_keys_ttl.py
from src.domain.cache.cache_keys import CacheKeys


def test_ttl_30_min_constant_exists():
    assert CacheKeys.TTL_30_MIN == 1800
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend/.worktrees/feature/redis-optimize
python -m pytest tests/unit/domain/cache/test_cache_keys_ttl.py -v
```

Expected: `FAILED — AttributeError: type object 'CacheKeys' has no attribute 'TTL_30_MIN'`

- [ ] **Step 3: Add TTL_30_MIN to CacheKeys**

In `src/domain/cache/cache_keys.py`, add after line 14 (`TTL_5_MIN = 300`):

```python
    TTL_30_MIN = 1800
```

- [ ] **Step 4: Add cachetools to requirements.txt**

Open `requirements.txt` and add the following line (alphabetically near other `c` packages):

```
cachetools>=5.3.0
```

- [ ] **Step 5: Install the dependency**

```bash
pip install cachetools>=5.3.0
```

- [ ] **Step 6: Run the test to confirm it passes**

```bash
python -m pytest tests/unit/domain/cache/test_cache_keys_ttl.py -v
```

Expected: `PASSED`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/domain/cache/cache_keys.py tests/unit/domain/cache/test_cache_keys_ttl.py
git commit -m "feat: add TTL_30_MIN constant and cachetools dependency"
```

---

## Task 2: Fix delete_pattern — KEYS → SCAN

**Files:**
- Modify: `src/infra/cache/redis_client.py`
- Test: `tests/unit/infra/test_redis_client_timeout.py` (add new test)

The current `delete_pattern` uses `await self.client.keys(pattern)` which blocks Redis while scanning the entire keyspace. Replace with `scan_iter` which yields keys in batches without blocking.

- [ ] **Step 1: Write a failing test for scan_iter behavior**

Add to `tests/unit/infra/test_redis_client_timeout.py`:

```python
@pytest.mark.asyncio
async def test_delete_pattern_uses_scan_not_keys():
    """delete_pattern must use scan_iter, never client.keys (blocking)."""
    from src.infra.cache.redis_client import RedisClient

    client = RedisClient.__new__(RedisClient)

    deleted_keys = []

    async def fake_scan_iter(match):
        for k in ["user:abc:macros:2026-01-01", "user:abc:macros:2026-01-02"]:
            yield k

    mock_client = AsyncMock()
    mock_client.scan_iter = fake_scan_iter
    mock_client.delete = AsyncMock(side_effect=lambda k: deleted_keys.append(k))
    client.client = mock_client

    count = await client.delete_pattern("user:abc:macros:*")

    assert count == 2
    assert "user:abc:macros:2026-01-01" in deleted_keys
    assert "user:abc:macros:2026-01-02" in deleted_keys
    assert mock_client.keys.call_count == 0  # must NOT use blocking KEYS
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
python -m pytest tests/unit/infra/test_redis_client_timeout.py::test_delete_pattern_uses_scan_not_keys -v
```

Expected: `FAILED — AssertionError: assert mock_client.keys.call_count == 0` (current impl calls `keys`)

- [ ] **Step 3: Replace the delete_pattern implementation**

In `src/infra/cache/redis_client.py`, find and replace the `delete_pattern` method:

```python
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern using non-blocking SCAN."""
        if not self.client:
            return 0
        try:
            deleted = 0
            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
                deleted += 1
            if deleted:
                logger.debug("Deleted %d keys matching %s", deleted, pattern)
            return deleted
        except RedisError as exc:
            logger.warning("Redis delete_pattern error for %s: %s", pattern, exc)
            return 0
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
python -m pytest tests/unit/infra/test_redis_client_timeout.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/infra/cache/redis_client.py tests/unit/infra/test_redis_client_timeout.py
git commit -m "fix: replace blocking KEYS with scan_iter in delete_pattern"
```

---

## Task 3: Extend daily_breakdown and weekly_budget TTLs

**Files:**
- Modify: `src/domain/cache/cache_keys.py:42-54`

These keys are invalidated correctly on every meal mutation and metric update, so a 30-minute TTL is safe and reduces SET frequency 3–6×.

- [ ] **Step 1: Write a failing test**

Add to `tests/unit/domain/cache/test_cache_keys_ttl.py`:

```python
def test_daily_breakdown_ttl_is_30_min():
    from datetime import date
    _, ttl = CacheKeys.daily_breakdown("user-1", date(2026, 1, 1))
    assert ttl == 1800, f"expected 1800, got {ttl}"


def test_weekly_budget_ttl_is_30_min():
    from datetime import date
    _, ttl = CacheKeys.weekly_budget("user-1", date(2026, 1, 1))
    assert ttl == 1800, f"expected 1800, got {ttl}"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/unit/domain/cache/test_cache_keys_ttl.py -v
```

Expected: `FAILED — assert 300 == 1800` and `assert 600 == 1800`

- [ ] **Step 3: Update the TTL values in cache_keys.py**

In `src/domain/cache/cache_keys.py`, change the `daily_breakdown` static method:

```python
    @staticmethod
    def daily_breakdown(user_id: str, week_start_date: date) -> tuple[str, int]:
        return (
            f"user:{user_id}:daily_breakdown:{week_start_date.isoformat()}",
            CacheKeys.TTL_30_MIN,
        )
```

Change the `weekly_budget` static method:

```python
    @staticmethod
    def weekly_budget(user_id: str, week_start_date: date) -> tuple[str, int]:
        """Cache key for weekly macro budget. 30 min TTL."""
        return (
            f"user:{user_id}:weekly_budget:{week_start_date.isoformat()}",
            CacheKeys.TTL_30_MIN,
        )
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/unit/domain/cache/test_cache_keys_ttl.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Run full unit suite to catch regressions**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: all previously-passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/domain/cache/cache_keys.py tests/unit/domain/cache/test_cache_keys_ttl.py
git commit -m "perf: extend daily_breakdown and weekly_budget cache TTL to 30 min"
```

---

## Task 4: In-memory auth UID cache (Option B)

**Files:**
- Create: `tests/unit/api/dependencies/test_auth_cache.py`
- Modify: `src/api/dependencies/auth_cache.py`

Every authenticated request currently does a Redis GET for `auth:uid:{firebase_uid}`. Replacing with a process-level `TTLCache` eliminates all Redis commands on this path.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/api/dependencies/test_auth_cache.py`:

```python
"""Tests for in-memory auth UID cache."""
import pytest


@pytest.fixture(autouse=True)
def clear_uid_cache():
    """Isolate tests — wipe the module-level TTLCache between runs."""
    from src.api.dependencies import auth_cache as module
    module._uid_cache.clear()
    yield
    module._uid_cache.clear()


@pytest.mark.asyncio
async def test_get_returns_none_on_cache_miss():
    from src.api.dependencies.auth_cache import get_cached_user_id
    result = await get_cached_user_id(None, "uid-unknown")
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_user_id_on_active_hit():
    from src.api.dependencies.auth_cache import get_cached_user_id, set_cached_user_id
    await set_cached_user_id(None, "uid-abc", "user-123", is_active=True)
    result = await get_cached_user_id(None, "uid-abc")
    assert result == "user-123"


@pytest.mark.asyncio
async def test_get_returns_none_for_inactive_user():
    from src.api.dependencies.auth_cache import get_cached_user_id, set_cached_user_id
    await set_cached_user_id(None, "uid-inactive", "user-456", is_active=False)
    result = await get_cached_user_id(None, "uid-inactive")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_removes_entry():
    from src.api.dependencies.auth_cache import (
        get_cached_user_id,
        invalidate_cached_user_id,
        set_cached_user_id,
    )
    await set_cached_user_id(None, "uid-del", "user-789", is_active=True)
    await invalidate_cached_user_id(None, "uid-del")
    result = await get_cached_user_id(None, "uid-del")
    assert result is None


@pytest.mark.asyncio
async def test_cache_service_arg_is_ignored():
    """cache_service=None must work — signature kept for backward compat only."""
    from src.api.dependencies.auth_cache import get_cached_user_id, set_cached_user_id
    await set_cached_user_id(None, "uid-x", "user-x", is_active=True)
    assert await get_cached_user_id(None, "uid-x") == "user-x"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/unit/api/dependencies/test_auth_cache.py -v
```

Expected: most tests `PASSED` coincidentally (old impl still calls Redis which fails silently with `cache_service=None`) but `test_get_returns_user_id_on_active_hit` will `FAIL` since set/get with `None` cache service returns None.

- [ ] **Step 3: Replace auth_cache.py with in-memory implementation**

Overwrite `src/api/dependencies/auth_cache.py` completely:

```python
"""Helpers for caching Firebase UID to active user ID lookups."""

from __future__ import annotations

import logging
from typing import Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# 10-minute in-process cache. Avoids a Redis round-trip on every authenticated
# request. maxsize=15_000 covers 10K+ active users with headroom.
_uid_cache: TTLCache[str, dict] = TTLCache(maxsize=15_000, ttl=600)


async def get_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
) -> Optional[str]:
    """Return cached database user ID only when the cached user is active."""
    entry = _uid_cache.get(firebase_uid)
    if not isinstance(entry, dict) or entry.get("is_active") is not True:
        return None
    user_id = entry.get("user_id")
    return str(user_id) if user_id else None


async def set_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
    user_id: str,
    is_active: bool,
) -> None:
    """Cache database user identity for the Firebase UID."""
    _uid_cache[firebase_uid] = {"user_id": str(user_id), "is_active": bool(is_active)}


async def invalidate_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
) -> None:
    """Invalidate cached Firebase UID mapping."""
    _uid_cache.pop(firebase_uid, None)
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/unit/api/dependencies/test_auth_cache.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 5: Run full unit suite**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: all previously-passing tests still pass (no callers break — signature unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/api/dependencies/auth_cache.py tests/unit/api/dependencies/test_auth_cache.py
git commit -m "perf: replace Redis auth UID cache with process-level TTLCache"
```

---

## Task 5: Refactor DailyContextPrecomputeService — remove Redis

**Files:**
- Modify: `src/infra/services/daily_context_precompute_service.py`
- Modify: `tests/unit/infra/test_daily_context_precompute_service.py`

Three changes in one file:
1. Add FCM eligibility filter (`EXISTS user_fcm_tokens`) to Query 1
2. Replace Redis sentinel (`redis.exists` / `redis.set`) with a module-level Python `set`
3. Remove the entire "Build Redis items" section; change `_precompute_db_sync` return type from `list[tuple[str, dict, int]]` to `int`
4. Remove `redis_client` constructor parameter

- [ ] **Step 1: Update existing tests for new constructor and sentinel**

Replace the first three tests in `tests/unit/infra/test_daily_context_precompute_service.py`:

```python
import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def clear_sentinel():
    """Wipe in-memory sentinel between tests to prevent leakage."""
    from src.infra.services import daily_context_precompute_service as module
    module._precomputed_today.clear()
    yield
    module._precomputed_today.clear()


@pytest.mark.asyncio
async def test_skips_if_sentinel_in_memory():
    """Pre-compute is skipped when (date, tz) already in _precomputed_today."""
    from src.infra.services import daily_context_precompute_service as module
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)
    module._precomputed_today.add((today.isoformat(), "Asia/Ho_Chi_Minh"))

    with patch.object(svc, "_precompute_db_sync") as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)
        mock_sync.assert_not_called()


@pytest.mark.asyncio
async def test_runs_and_adds_to_sentinel_set():
    """Pre-compute runs and adds (date, tz) to _precomputed_today on success."""
    from src.infra.services import daily_context_precompute_service as module
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    today = date(2026, 4, 22)

    with patch.object(svc, "_precompute_db_sync", return_value=0):
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", today)

    assert (today.isoformat(), "Asia/Ho_Chi_Minh") in module._precomputed_today


def test_sentinel_key_format():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService()
    key = svc.sentinel_key(date(2026, 4, 22), "Asia/Ho_Chi_Minh")
    assert key == "precomputed:2026-04-22:Asia/Ho_Chi_Minh"
```

Also update `test_user_calorie_goal_uses_adjusted_weekly_budget_target` (line ~77) — it constructs `DailyContextPrecomputeService(redis_client=MagicMock())`. Change that line to `DailyContextPrecomputeService()`.

Remove the test `test_context_key_format` — `context_key()` method will be removed.

- [ ] **Step 2: Run tests to confirm the right failures**

```bash
python -m pytest tests/unit/infra/test_daily_context_precompute_service.py -v
```

Expected: failures on `test_skips_if_sentinel_in_memory`, `test_runs_and_adds_to_sentinel_set`, and any test constructing `DailyContextPrecomputeService(redis_client=...)`.

- [ ] **Step 3: Update DailyContextPrecomputeService — constructor + sentinel**

At the top of `src/infra/services/daily_context_precompute_service.py`, after the imports, add the module-level sentinel set:

```python
# Single-process sentinel: the leader lock ensures only one process runs this.
# Cleared on restart, which is correct — startup catch-up reruns the precompute.
_precomputed_today: set[tuple[str, str]] = set()
```

Replace the `__init__`, `sentinel_key`, `is_precomputed`, and `context_key` methods, and `precompute_for_timezone`:

```python
    def __init__(self) -> None:
        self._tdee_service = TdeeCalculationService()
        self._locks: dict[str, asyncio.Lock] = {}

    def sentinel_key(self, today: date, tz_name: str) -> str:
        """Kept for logging and test assertions."""
        return f"precomputed:{today.isoformat()}:{tz_name}"

    async def is_precomputed(self, today: date, tz_name: str) -> bool:
        return (today.isoformat(), tz_name) in _precomputed_today

    async def precompute_for_timezone(self, tz_name: str, today: date) -> None:
        """No-op if sentinel exists; otherwise runs DB sync work in thread pool."""
        if await self.is_precomputed(today, tz_name):
            logger.debug(
                "Pre-compute sentinel hit for %s on %s — skipping", tz_name, today
            )
            return

        lock_key = f"{today.isoformat()}:{tz_name}"
        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()
        async with self._locks[lock_key]:
            if await self.is_precomputed(today, tz_name):
                logger.debug(
                    "Pre-compute sentinel hit for %s on %s — skipping", tz_name, today
                )
                return

            logger.debug(
                "Pre-computing notification context for %s on %s", tz_name, today
            )
            count = await asyncio.to_thread(
                self._precompute_db_sync, tz_name, today
            )
            _precomputed_today.add((today.isoformat(), tz_name))
            logger.debug(
                "Pre-compute complete for %s: %d users", tz_name, count
            )
```

Remove `context_key` method entirely (no longer used).

- [ ] **Step 4: Update _precompute_db_sync — FCM filter + remove Redis hash build**

In `_precompute_db_sync`, update the return type annotation and Query 1 (the first SQL query, currently filtering by `u.timezone`, `u.is_active`, `np.is_deleted`):

Change the method signature from:
```python
    def _precompute_db_sync(
        self, tz_name: str, today: date
    ) -> list[tuple[str, dict, int]]:
```

To:
```python
    def _precompute_db_sync(self, tz_name: str, today: date) -> int:
        """
        All DB work: 5 SQL queries + 1 bulk INSERT.
        Returns count of users processed.
        Only processes users with at least one active FCM token.
        """
```

Update Query 1 — add the `AND EXISTS` clause before the closing parenthesis of the WHERE block:

```python
            pref_rows = session.execute(
                text("""
                    SELECT
                        np.user_id,
                        np.meal_reminders_enabled,
                        np.daily_summary_enabled,
                        np.breakfast_time_minutes,
                        np.lunch_time_minutes,
                        np.dinner_time_minutes,
                        np.daily_summary_time_minutes,
                        np.language
                    FROM notification_preferences np
                    JOIN users u ON u.id = np.user_id
                    WHERE u.timezone = :tz_name
                      AND u.is_active = true
                      AND np.is_deleted = false
                      AND EXISTS (
                          SELECT 1 FROM user_fcm_tokens t
                          WHERE t.user_id = np.user_id AND t.is_active = true
                      )
                """),
                {"tz_name": tz_name},
            ).fetchall()
```

At the end of the method, replace the entire "Build Redis items" section (the final `for pref_row in pref_rows` loop and `return redis_items`) with:

```python
            return len(pref_rows)
```

Also remove the `_CONTEXT_TTL` and `_SENTINEL_TTL` module-level constants since they are no longer used.

Remove `from src.infra.cache.redis_client import RedisClient` from the imports.

- [ ] **Step 5: Run tests to confirm passing**

```bash
python -m pytest tests/unit/infra/test_daily_context_precompute_service.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Run full unit suite**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: all previously-passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add src/infra/services/daily_context_precompute_service.py tests/unit/infra/test_daily_context_precompute_service.py
git commit -m "perf: remove Redis from notification precompute; add FCM eligibility filter"
```

---

## Task 6: Replace HGETALL with PG batch query in ScheduledNotificationService

**Files:**
- Modify: `src/infra/services/scheduled_notification_service.py`
- Modify: `tests/unit/infra/test_scheduled_notification_service.py`

This is the last Redis command removed from the notification path. At send-time, instead of `hgetall_batch` fetching stale Redis hashes, a single batch PG query returns real-time `calories_consumed` for all meal-reminder users in that tick.

- [ ] **Step 1: Update the existing scheduler test**

In `tests/unit/infra/test_scheduled_notification_service.py`, update `test_send_loop_marks_notifications_sent` to remove the `mock_redis.hgetall_batch` mock and replace with a mock for the new PG helper:

```python
@pytest.mark.asyncio
async def test_send_loop_marks_notifications_sent():
    from src.infra.services.scheduled_notification_service import (
        ScheduledNotificationService,
    )

    mock_notif = MagicMock()
    mock_notif.notification_type = "meal_reminder_breakfast"
    mock_notif.context = {
        "fcm_tokens": ["tok1"],
        "calorie_goal": 1800,
        "gender": "male",
        "language_code": "en",
    }
    mock_notif.id = "notif-id-1"
    mock_notif.user_id = "user-1"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = mock_firebase
    svc._running = True

    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as mock_qb, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ) as mock_uow, patch(
        "src.infra.services.scheduled_notification_service._fetch_calories_consumed_batch",
        return_value={"user-1": 400},
    ):
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = MagicMock()

        now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

        mock_firebase.send_multicast.assert_called_once()
```

- [ ] **Step 2: Run test to confirm failure**

```bash
python -m pytest tests/unit/infra/test_scheduled_notification_service.py::test_send_loop_marks_notifications_sent -v
```

Expected: `FAILED` — either `AttributeError: _fetch_calories_consumed_batch` doesn't exist yet, or the mock_redis attribute error.

- [ ] **Step 3: Add timedelta import to scheduled_notification_service.py**

In `src/infra/services/scheduled_notification_service.py`, change:

```python
from datetime import datetime, timezone
```

To:

```python
from datetime import datetime, timedelta, timezone
```

- [ ] **Step 4: Add _fetch_calories_consumed_batch module-level function**

At the bottom of `src/infra/services/scheduled_notification_service.py`, after the `_chunked` helper and before `_seconds_until_next_minute`, add:

```python
def _fetch_calories_consumed_batch(
    user_ids: list[str], now: datetime
) -> dict[str, int]:
    """Batch-fetch calories consumed in the last 24 hours per user.

    Uses a 24-hour lookback from now. Meal reminders fire mid-day locally,
    so a 24-hour window captures all of the user's current-day meals.
    This replaces the Redis HGETALL that fetched a stale midnight snapshot.
    """
    window_start = now - timedelta(hours=24)
    with UnitOfWork() as uow:
        rows = uow.session.execute(
            text("""
                SELECT m.user_id,
                       COALESCE(SUM(
                           (n.protein * 4.0)
                           + (GREATEST(n.carbs - n.fiber, 0) * 4.0)
                           + (n.fiber * 2.0)
                           + (n.fat * 9.0)
                       ), 0) AS consumed_calories
                FROM meal m
                JOIN nutrition n ON n.meal_id = m.meal_id
                WHERE m.user_id = ANY(:ids)
                  AND m.created_at >= :start
                  AND m.status = 'READY'
                GROUP BY m.user_id
            """),
            {
                "ids": user_ids,
                "start": window_start.replace(tzinfo=None),
            },
        ).fetchall()
    return {row.user_id: int(round(row.consumed_calories)) for row in rows}
```

- [ ] **Step 5: Update _send_due_notifications to use PG query**

In `_send_due_notifications`, replace the Redis hgetall_batch block:

**Remove these lines** (currently lines ~204-206):
```python
        # Batch-fetch calories_consumed from Redis
        context_keys = [f"user_daily_context:{n.user_id}" for n in due]
        redis_contexts = await self._redis.hgetall_batch(context_keys)
```

**Replace with:**
```python
        # Batch-fetch real-time calories_consumed from DB for meal reminders.
        # daily_summary uses the JSONB snapshot; trial_expiry ignores calories.
        meal_reminder_ids = [
            n.user_id for n in due
            if n.notification_type.startswith("meal_reminder")
        ]
        consumed_map: dict[str, int] = {}
        if meal_reminder_ids:
            consumed_map = await asyncio.to_thread(
                _fetch_calories_consumed_batch, meal_reminder_ids, now
            )
```

Then update the per-notification loop. Replace the block that reads from `redis_ctx`:

**Remove:**
```python
            if notif.notification_type == "daily_summary":
                # Use JSONB snapshot from midnight pre-compute (stable for full-day summary)
                calories_consumed = int(ctx.get("calories_consumed", 0))
            elif notif.notification_type.startswith("trial_expiry"):
                # Trial reminders don't depend on calorie data; skip Redis to avoid
                # a "cache miss" WARNING per row.
                calories_consumed = 0
            else:
                # Use Redis for meal reminders (fresher, ~30 min stale)
                if not redis_ctx:
                    logger.warning(
                        "Redis cache miss for user %s — using calorie_goal only",
                        notif.user_id,
                    )
                    calories_consumed = 0
                else:
                    calories_consumed = int(redis_ctx.get("calories_consumed", 0))
```

**Replace with:**
```python
            if notif.notification_type == "daily_summary":
                # JSONB snapshot from midnight pre-compute (stable for full-day summary)
                calories_consumed = int(ctx.get("calories_consumed", 0))
            elif notif.notification_type.startswith("trial_expiry"):
                calories_consumed = 0
            else:
                # meal_reminder_* — real-time DB data
                calories_consumed = consumed_map.get(notif.user_id, 0)
```

Also update the `for notif, redis_ctx in zip(due, redis_contexts):` loop header — change to:

```python
        for notif in due:
```

- [ ] **Step 6: Update ScheduledNotificationService.__init__ — remove Redis from DailyContextPrecomputeService**

In `__init__`, change:

```python
        self._precompute = DailyContextPrecomputeService(redis_client)
```

To:

```python
        self._precompute = DailyContextPrecomputeService()
```

- [ ] **Step 7: Remove redis_client from ScheduledNotificationService constructor**

`self._redis` is now unused — only referenced in the constructor store and the `hgetall_batch` call you just removed.

In `src/infra/services/scheduled_notification_service.py`:

Remove the import:
```python
from src.infra.cache.redis_client import RedisClient  # delete this line
```

Change `__init__` signature and body:
```python
    def __init__(
        self,
        firebase_service: FirebaseService,
        trial_push_service: "ScheduledSubscriptionPushService | None" = None,
    ):
        self._firebase = firebase_service
        self._precompute = DailyContextPrecomputeService()
        self._trial_push = trial_push_service
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._leader_lock = SchedulerLeaderLock()
        self._leader_acquired = False
        self._cleanup_counter = 0
        self._distinct_timezones: list[str] = []

        if self._trial_push is None:
            logger.warning(
                "ScheduledNotificationService constructed without "
                "trial_push_service — trial reminders disabled"
            )
        else:
            logger.info("ScheduledNotificationService: trial_push scheduler active")
```

Update the call site in `src/api/base_dependencies.py` (line ~337):
```python
        _scheduled_notification_service = ScheduledNotificationService(
            firebase_service,
            trial_push_service=trial_push_service,
        )
```

- [ ] **Step 8: Run tests to confirm passing**

```bash
python -m pytest tests/unit/infra/test_scheduled_notification_service.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 9: Run full unit suite**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: 1336+ tests passing, 0 failures.

- [ ] **Step 10: Commit**

```bash
git add src/infra/services/scheduled_notification_service.py tests/unit/infra/test_scheduled_notification_service.py
git commit -m "perf: replace Redis HGETALL with PG batch query for notification calories"
```

---

## Final Verification

- [ ] **Run the full test suite one last time**

```bash
python -m pytest tests/unit/ -q --tb=short
```

Expected: all tests pass, 0 failures.

- [ ] **Verify no Redis hash operations remain in the notification path**

```bash
grep -rn "hset_batch\|hgetall_batch\|user_daily_context\|precomputed:" \
  src/infra/services/daily_context_precompute_service.py \
  src/infra/services/scheduled_notification_service.py
```

Expected: no output (all occurrences removed).

- [ ] **Verify auth_cache no longer imports CachePort for Redis**

```bash
grep -n "cache_service\|CachePort\|CacheKeys" src/api/dependencies/auth_cache.py
```

Expected: none of these imports remain.
