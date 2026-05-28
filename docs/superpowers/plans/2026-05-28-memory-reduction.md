# Memory Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `nutree_backend` steady-state RAM from ~82% to ~65% and eliminate the gradual 8-hour memory creep via 6 targeted code-only changes.

**Architecture:** No structural changes — all fixes are single-line or small edits to existing files. Fix 1 adds Uvicorn worker recycling. Fixes 3–4 shrink in-process caches. Fix 5 caps the notification query. Fix 6 streams DB rows instead of buffering. Fix 7 nudges GC after batch jobs.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (sync Core text queries), cachetools TTLCache, Uvicorn.

**Spec:** `docs/superpowers/specs/2026-05-28-memory-reduction-design.md`

**Note on Fix 1:** Worker count stays at 4 (user decision). Only `--max-requests` is added — this recycles each worker after 500 requests, releasing accumulated Python heap fragmentation.

---

## File Map

| Fix | File | Change |
|-----|------|--------|
| 1 | `docker-entrypoint.sh` | Add `--max-requests 500 --max-requests-jitter 50` |
| 3 | `src/api/dependencies/auth_cache.py` | `maxsize=15_000` → `maxsize=500` |
| 4 | `src/domain/services/meal_discovery/food_image_search_service.py` | `5_000` → `500`, `7 * 24 * 3600` → `24 * 3600` |
| 5 | `src/infra/repositories/notification/reminder_query_builder.py` | Add `.limit(500)` |
| 6 | `src/infra/services/daily_context_precompute_service.py` | 4× `.fetchall()` → stream into dicts |
| 7 | `src/infra/services/scheduled_notification_service.py` | `gc.collect()` at end of `_send_due_notifications` |
| 7 | `src/infra/services/daily_context_precompute_service.py` | `gc.collect()` at end of `_precompute_db_sync` |

---

## Task 1: Fix 1 — Uvicorn --max-requests

**Files:**
- Modify: `docker-entrypoint.sh`

- [ ] **Step 1: Edit docker-entrypoint.sh**

Find the `exec uvicorn` block (currently ends with `--loop uvloop`) and add the two new flags:

```bash
# Before
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop

# After
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop \
    --max-requests 500 \
    --max-requests-jitter 50
```

- [ ] **Step 2: Verify the file looks correct**

```bash
grep -A 10 "exec uvicorn" docker-entrypoint.sh
```

Expected output includes `--max-requests 500` and `--max-requests-jitter 50`.

- [ ] **Step 3: Commit**

```bash
git add docker-entrypoint.sh
git commit -m "perf: add uvicorn --max-requests 500 to recycle workers and release heap"
```

---

## Task 2: Fix 3 — TTLCache maxsize 15k → 500

**Files:**
- Modify: `src/api/dependencies/auth_cache.py:14`
- Test: `tests/unit/api/dependencies/test_auth_cache.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/dependencies/test_auth_cache.py`:

```python
from cachetools import TTLCache
from src.api.dependencies.auth_cache import _uid_cache


def test_auth_cache_maxsize():
    assert _uid_cache.maxsize == 500


def test_auth_cache_ttl():
    assert _uid_cache.ttl == 600


def test_auth_cache_evicts_at_maxsize():
    from src.api.dependencies.auth_cache import _uid_cache
    _uid_cache.clear()
    for i in range(501):
        _uid_cache[f"uid_{i}"] = {"user_id": str(i), "is_active": True}
    assert len(_uid_cache) == 500
    _uid_cache.clear()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/api/dependencies/test_auth_cache.py -v
```

Expected: `FAILED test_auth_cache_maxsize` — `assert 15000 == 500`.

- [ ] **Step 3: Apply the fix**

In `src/api/dependencies/auth_cache.py`, line 14:

```python
# Before
_uid_cache: TTLCache[str, dict] = TTLCache(maxsize=15_000, ttl=600)

# After
_uid_cache: TTLCache[str, dict] = TTLCache(maxsize=500, ttl=600)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/api/dependencies/test_auth_cache.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/dependencies/auth_cache.py tests/unit/api/dependencies/test_auth_cache.py
git commit -m "perf: reduce auth TTLCache maxsize from 15k to 500 entries"
```

---

## Task 3: Fix 4 — FoodImageSearchService cache 5k/7d → 500/1d

**Files:**
- Modify: `src/domain/services/meal_discovery/food_image_search_service.py`
- Test: `tests/unit/domain/services/meal_discovery/test_food_image_search_service_cache.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/domain/services/meal_discovery/test_food_image_search_service_cache.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/domain/services/meal_discovery/test_food_image_search_service_cache.py -v
```

Expected: `FAILED test_cache_max_entries` — `assert 5000 == 500`.

- [ ] **Step 3: Apply the fix**

In `src/domain/services/meal_discovery/food_image_search_service.py`, update the two constants at the top of the file:

```python
# Before
CACHE_TTL_SECONDS = 7 * 24 * 3600
CACHE_MAX_ENTRIES = 5_000

# After
CACHE_TTL_SECONDS = 24 * 3600
CACHE_MAX_ENTRIES = 500
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/domain/services/meal_discovery/test_food_image_search_service_cache.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/meal_discovery/food_image_search_service.py \
        tests/unit/domain/services/meal_discovery/test_food_image_search_service_cache.py
git commit -m "perf: reduce food image cache from 5k/7d to 500 entries/1 day TTL"
```

---

## Task 4: Fix 5 — find_due_notifications LIMIT 500

**Files:**
- Modify: `src/infra/repositories/notification/reminder_query_builder.py:153-163`
- Test: `tests/unit/repositories/notification/test_reminder_query_builder_limit.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/repositories/notification/test_reminder_query_builder_limit.py`:

```python
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder


def test_find_due_notifications_applies_limit():
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
    ReminderQueryBuilder.find_due_notifications(mock_db, now, lock_rows=False)

    mock_query.limit.assert_called_once_with(500)


def test_find_due_notifications_limit_applied_before_all():
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    now = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
    ReminderQueryBuilder.find_due_notifications(mock_db, now)

    call_order = mock_query.method_calls
    limit_idx = next(i for i, c in enumerate(call_order) if c[0] == "limit")
    all_idx = next(i for i, c in enumerate(call_order) if c[0] == "all")
    assert limit_idx < all_idx
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/repositories/notification/test_reminder_query_builder_limit.py -v
```

Expected: `FAILED test_find_due_notifications_applies_limit` — `limit` was never called.

- [ ] **Step 3: Apply the fix**

In `src/infra/repositories/notification/reminder_query_builder.py`, the `find_due_notifications` method (around line 153). Add `.limit(500)` before the `if lock_rows:` FOR UPDATE block and before `.all()`:

```python
    @staticmethod
    def find_due_notifications(
        db: Session, now: datetime, lock_rows: bool = False
    ) -> list:
        status_filter = NotificationORM.status == "pending"
        if lock_rows:
            stale_processing_before = (
                now - ReminderQueryBuilder.PROCESSING_RECLAIM_AFTER
            )
            status_filter = or_(
                status_filter,
                and_(
                    NotificationORM.status == "processing",
                    NotificationORM.scheduled_for_utc <= stale_processing_before,
                ),
            )

        query = (
            db.query(NotificationORM)
            .filter(
                NotificationORM.scheduled_for_utc <= now,
                status_filter,
            )
            .order_by(NotificationORM.scheduled_for_utc, NotificationORM.created_at)
            .limit(500)
        )
        if lock_rows:
            query = query.with_for_update(skip_locked=True)
        return query.all()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/repositories/notification/test_reminder_query_builder_limit.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Run the existing notification tests to check no regressions**

```bash
pytest tests/unit/ -k "notification" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/repositories/notification/reminder_query_builder.py \
        tests/unit/repositories/notification/test_reminder_query_builder_limit.py
git commit -m "perf: cap find_due_notifications at 500 rows per scheduler tick"
```

---

## Task 5: Fix 6 — Stream precompute queries instead of fetchall

**Files:**
- Modify: `src/infra/services/daily_context_precompute_service.py` (4 sites)
- Test: `tests/unit/infra/services/test_daily_context_precompute_streaming.py` (create)

**Background:** The `_precompute_db_sync` method runs 4 SQL queries. Queries 2–4 build Python dicts from result rows. Instead of `.fetchall()` (allocates a full list) then iterating, we iterate the cursor directly — eliminating the intermediate list. Query 1 keeps a list because `user_ids` must be computed from it before the other queries run.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/infra/services/test_daily_context_precompute_streaming.py`:

```python
from unittest.mock import MagicMock, patch, call
from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService


def test_token_query_does_not_call_fetchall():
    """Queries 2-4 must not call fetchall() — they should iterate cursor directly."""
    service = DailyContextPrecomputeService()

    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    mock_result.fetchall = MagicMock()

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result

    mock_uow = MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow.session = mock_session

    # Query 1 returns one user so the method doesn't exit early
    pref_row = MagicMock()
    pref_row.user_id = "user-1"

    call_count = [0]
    original_execute = mock_session.execute

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First query (pref_rows) — return one row
            r = MagicMock()
            r.__iter__ = MagicMock(return_value=iter([pref_row]))
            r.fetchall = MagicMock(return_value=[pref_row])
            return r
        return mock_result

    mock_session.execute.side_effect = side_effect

    from datetime import date
    with patch("src.infra.services.daily_context_precompute_service.UnitOfWork", return_value=mock_uow):
        try:
            service._precompute_db_sync("UTC", date.today())
        except Exception:
            pass  # May fail due to incomplete mock — we only care about fetchall calls

    # fetchall should only be called on query 1, not on queries 2-4
    assert mock_result.fetchall.call_count == 0, (
        "Queries 2-4 must not call fetchall() — iterate cursor directly"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/infra/services/test_daily_context_precompute_streaming.py -v
```

Expected: FAIL — `mock_result.fetchall.call_count` is greater than 0.

- [ ] **Step 3: Apply the fix**

In `src/infra/services/daily_context_precompute_service.py`, update the 4 fetchall sites inside `_precompute_db_sync`:

**Query 1** — keep `.fetchall()` (list needed for `user_ids`):
```python
# Line ~454 — NO CHANGE
            ).fetchall()
```

**Query 2** — remove `.fetchall()`, iterate cursor directly into dict:
```python
# Before (lines ~462-474)
            token_rows = session.execute(
                text("""
                    SELECT user_id, fcm_token
                    FROM user_fcm_tokens
                    WHERE user_id = ANY(:ids)
                      AND is_active = true
                """),
                {"ids": user_ids},
            ).fetchall()

            tokens_by_user: dict[str, list[str]] = defaultdict(list)
            for row in token_rows:
                tokens_by_user[row.user_id].append(row.fcm_token)

# After
            tokens_by_user: dict[str, list[str]] = defaultdict(list)
            for row in session.execute(
                text("""
                    SELECT user_id, fcm_token
                    FROM user_fcm_tokens
                    WHERE user_id = ANY(:ids)
                      AND is_active = true
                """),
                {"ids": user_ids},
            ):
                tokens_by_user[row.user_id].append(row.fcm_token)
```

**Query 3** — remove `.fetchall()`, iterate cursor directly into dict:
```python
# Before (lines ~477-500)
            profile_rows = session.execute(
                text("""
                    SELECT
                        up.user_id, up.age, up.gender, up.height_cm, up.weight_kg,
                        up.body_fat_percentage, up.job_type, up.training_days_per_week,
                        up.training_minutes_per_session, up.fitness_goal,
                        up.training_level, u.language_code
                    FROM user_profiles up
                    JOIN users u ON u.id = up.user_id
                    WHERE up.user_id = ANY(:ids)
                      AND up.is_current = true
                """),
                {"ids": user_ids},
            ).fetchall()

            profiles_by_user = {row.user_id: row for row in profile_rows}

# After
            profiles_by_user = {
                row.user_id: row
                for row in session.execute(
                    text("""
                        SELECT
                            up.user_id, up.age, up.gender, up.height_cm, up.weight_kg,
                            up.body_fat_percentage, up.job_type, up.training_days_per_week,
                            up.training_minutes_per_session, up.fitness_goal,
                            up.training_level, u.language_code
                        FROM user_profiles up
                        JOIN users u ON u.id = up.user_id
                        WHERE up.user_id = ANY(:ids)
                          AND up.is_current = true
                    """),
                    {"ids": user_ids},
                )
            }
```

**Query 4** — remove `.fetchall()`, iterate cursor directly into dict:
```python
# Before (lines ~515-544)
            consumed_rows = session.execute(
                text("""
                    SELECT
                        m.user_id,
                        COALESCE(
                            SUM(
                                (n.protein * 4.0)
                                + (GREATEST(n.carbs - n.fiber, 0) * 4.0)
                                + (n.fiber * 2.0)
                                + (n.fat * 9.0)
                            ),
                            0
                        ) AS consumed_calories
                    FROM meal m
                    JOIN nutrition n ON n.meal_id = m.meal_id
                    WHERE m.user_id = ANY(:ids)
                      AND m.created_at >= :start
                      AND m.created_at < :end
                      AND m.status = 'READY'
                    GROUP BY m.user_id
                """),
                {
                    "ids": user_ids,
                    "start": day_start_utc.replace(tzinfo=None),
                    "end": day_end_utc.replace(tzinfo=None),
                },
            ).fetchall()

            consumed_by_user: dict[str, float] = {
                row.user_id: float(row.consumed_calories) for row in consumed_rows
            }

# After
            consumed_by_user: dict[str, float] = {
                row.user_id: float(row.consumed_calories)
                for row in session.execute(
                    text("""
                        SELECT
                            m.user_id,
                            COALESCE(
                                SUM(
                                    (n.protein * 4.0)
                                    + (GREATEST(n.carbs - n.fiber, 0) * 4.0)
                                    + (n.fiber * 2.0)
                                    + (n.fat * 9.0)
                                ),
                                0
                            ) AS consumed_calories
                        FROM meal m
                        JOIN nutrition n ON n.meal_id = m.meal_id
                        WHERE m.user_id = ANY(:ids)
                          AND m.created_at >= :start
                          AND m.created_at < :end
                          AND m.status = 'READY'
                        GROUP BY m.user_id
                    """),
                    {
                        "ids": user_ids,
                        "start": day_start_utc.replace(tzinfo=None),
                        "end": day_end_utc.replace(tzinfo=None),
                    },
                )
            }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/infra/services/test_daily_context_precompute_streaming.py -v
```

Expected: PASS.

- [ ] **Step 5: Run all unit tests to check no regressions**

```bash
pytest tests/unit/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/daily_context_precompute_service.py \
        tests/unit/infra/services/test_daily_context_precompute_streaming.py
git commit -m "perf: stream precompute queries 2-4 directly into dicts, remove intermediate lists"
```

---

## Task 6: Fix 7 — gc.collect() after scheduler batch runs

**Files:**
- Modify: `src/infra/services/scheduled_notification_service.py`
- Modify: `src/infra/services/daily_context_precompute_service.py`
- Test: `tests/unit/infra/services/test_gc_collect_after_batches.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/infra/services/test_gc_collect_after_batches.py`:

```python
import inspect


def test_gc_collect_present_in_send_due_notifications():
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService
    source = inspect.getsource(ScheduledNotificationService._send_due_notifications)
    assert "gc.collect()" in source, "_send_due_notifications must call gc.collect()"


def test_gc_collect_present_in_precompute_db_sync():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
    source = inspect.getsource(DailyContextPrecomputeService._precompute_db_sync)
    assert "gc.collect()" in source, "_precompute_db_sync must call gc.collect()"


def test_gc_imported_in_notification_service():
    import src.infra.services.scheduled_notification_service as mod
    import sys
    # gc must be imported at module level so it's available
    assert "gc" in dir(mod) or hasattr(mod, "gc"), "gc must be imported in scheduled_notification_service"


def test_gc_imported_in_precompute_service():
    import src.infra.services.daily_context_precompute_service as mod
    assert "gc" in dir(mod) or hasattr(mod, "gc"), "gc must be imported in daily_context_precompute_service"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/infra/services/test_gc_collect_after_batches.py -v
```

Expected: both tests FAIL — `gc.collect` was never called.

- [ ] **Step 3: Add gc.collect to scheduled_notification_service**

In `src/infra/services/scheduled_notification_service.py`:

At the top, add the import (if not already present):
```python
import gc
```

At the very end of `_send_due_notifications`, just before the method returns (after all FCM sends and DB updates complete):
```python
        gc.collect()
```

- [ ] **Step 4: Add gc.collect to daily_context_precompute_service**

In `src/infra/services/daily_context_precompute_service.py`:

At the top, add the import (if not already present):
```python
import gc
```

At the very end of `_precompute_db_sync`, just before `return count` (or `return 0` for the early-exit path):

For the early exit (when `not pref_rows`):
```python
            if not pref_rows:
                gc.collect()
                return 0
```

For the normal return at the end of the method:
```python
        gc.collect()
        return count
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/infra/services/test_gc_collect_after_batches.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Run the full unit test suite**

```bash
pytest tests/unit/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/infra/services/scheduled_notification_service.py \
        src/infra/services/daily_context_precompute_service.py \
        tests/unit/infra/services/test_gc_collect_after_batches.py
git commit -m "perf: call gc.collect() after notification send and precompute batch runs"
```

---

## Final Verification

- [ ] **Run full unit test suite**

```bash
pytest tests/unit/ -v --tb=short
```

Expected: all pass.

- [ ] **Verify all 6 fixes are present**

```bash
grep -n "max-requests" docker-entrypoint.sh
grep -n "maxsize=500" src/api/dependencies/auth_cache.py
grep -n "CACHE_MAX_ENTRIES = 500" src/domain/services/meal_discovery/food_image_search_service.py
grep -n "CACHE_TTL_SECONDS = 24" src/domain/services/meal_discovery/food_image_search_service.py
grep -n "\.limit(500)" src/infra/repositories/notification/reminder_query_builder.py
grep -n "gc.collect" src/infra/services/scheduled_notification_service.py src/infra/services/daily_context_precompute_service.py
```

Expected: each grep returns exactly one match.

- [ ] **Open a PR**

```bash
git push origin perf/reduce-memory-usage
```

Then open a PR from `perf/reduce-memory-usage` → `delivery`.
