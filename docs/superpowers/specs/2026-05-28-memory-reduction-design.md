# Memory Reduction Design

**Date:** 2026-05-28
**Branch:** perf/reduce-memory-usage
**Based on:** delivery

## Problem

`nutree_backend` (Render Standard, 2 GB RAM) consistently runs at 79–82% memory (1.6–1.76 GB). There is a gradual creep of ~150 MB over 8 hours. This leaves almost no headroom before OOM kills.

**Root cause breakdown (from Render metrics + code audit):**

| Cause | Contribution |
|-------|-------------|
| 4 Uvicorn workers × ~400 MB each | ~1.6 GB baseline |
| FoodImageSearchService 5k-entry / 7-day in-memory cache filling up | ~30–50 MB constant |
| TTLCache auth cache (15k maxsize) | ~15–20 MB constant |
| `find_due_notifications` no LIMIT — loads entire pending table every 60s | memory spike during scheduler runs |
| `daily_context_precompute_service` — 4 unbounded fetchall() per timezone | large spike during nightly job |
| Python heap fragmentation from request cycles | gradual creep between restarts |

**Target state:** Steady-state RAM ≤ 50% of limit (~1 GB), no gradual creep.

---

## Fix 1 — Reduce Uvicorn workers from 4 → 2 + add --max-requests

**File:** `docker-entrypoint.sh`

**Why workers=4 is wrong here:** Each Uvicorn worker is a separate Python process that independently loads every imported package (LangChain, Firebase admin, gRPC, Google AI SDK, Sentry, OpenTelemetry, etc.). On a 1-CPU Render Standard instance with async FastAPI, 4 workers means 4 copies of ~400 MB of loaded packages = 1.6 GB baseline. FastAPI with asyncio handles high I/O concurrency within a single worker; multiple workers exist for CPU parallelism, which this app doesn't benefit from on a 1-CPU box.

**Change:** Default `UVICORN_WORKERS` from `4` to `2`.

Two workers: 2 × 400 MB = ~800 MB baseline. This alone drops RAM from 80% to ~40%, providing 800 MB of headroom.

**Also add `--max-requests`:** Python's memory allocator (glibc malloc) does not return freed heap pages to the OS after request processing. After thousands of requests the heap fragments and stays inflated. Uvicorn's `--max-requests N` gracefully recycles a worker after N requests, releasing its entire heap. New workers start clean at ~400 MB.

```
--max-requests 500 --max-requests-jitter 50
```

`--max-requests-jitter 50` staggers recycling so both workers never restart simultaneously.

**Also update async DB pool size:** `config_async.py` calculates pool size as `UVICORN_WORKERS × ASYNC_POOL_SIZE_PER_WORKER` using `os.getenv("UVICORN_WORKERS", "4")` independently of the entrypoint. Both the entrypoint default and `config_async.py` default must be changed from `4` to `2` so the pool size drops from 12 → 6 connections.

**Expected saving:** ~800 MB baseline reduction.

---

## Fix 3 — Reduce TTLCache auth cache: 15k → 500 entries

**File:** `src/api/dependencies/auth_cache.py:14`

**Current:** `TTLCache(maxsize=15_000, ttl=600)`

**Why 15k is excessive:** At the observed traffic peak (56 req/min), concurrent active Firebase UIDs in the 10-minute TTL window is well under 500. 15k was sized for 10k+ simultaneous active users — far beyond current scale.

**Change:** `TTLCache(maxsize=500, ttl=600)`

When the cache is full, `cachetools` evicts the oldest entry (LRU). Excess requests fall through to a DB lookup, which is the safe fallback. No functional change.

**Expected saving:** ~15 MB.

---

## Fix 4 — Reduce FoodImageSearchService cache: 5k/7d → 500/1d

**File:** `src/domain/services/meal_discovery/food_image_search_service.py`

**Current:** `CACHE_MAX_ENTRIES = 5_000`, `CACHE_TTL_SECONDS = 7 * 24 * 3600`

**Why this accumulates:** The cache is an `OrderedDict` inside a singleton service. It fills to 5000 food-name → image-URL pairs and holds each entry for 7 days. At peak usage it stays at or near its maximum size indefinitely.

**Change:**
- `CACHE_MAX_ENTRIES = 500`
- `CACHE_TTL_SECONDS = 24 * 3600` (1 day)

Image URLs from Unsplash are stable for days. A 1-day TTL provides effective caching. 500 entries covers the realistic "hot" food vocabulary at current scale.

**Expected saving:** ~30–50 MB constant.

---

## Fix 5 — Add LIMIT to `find_due_notifications` + batch processing

**File:** `src/infra/repositories/notification/reminder_query_builder.py:153`

**Current:** `.all()` with no LIMIT — loads the entire pending notification table into RAM every 60 seconds.

**Why this spikes:** If the scheduler has any lag (redeploy, cold start, backlog), all pending rows are pulled into Python as ORM objects. `NotificationORM` includes JSONB `context` columns. A 10k-row backlog could spike 100+ MB.

**Change:** Add `.limit(500)` to `find_due_notifications`. The scheduler processes at most 500 notifications per tick (every 60s = 500/min throughput, more than enough at current scale). A backlog is drained across multiple ticks.

```python
query = (
    db.query(NotificationORM)
    .filter(...)
    .order_by(NotificationORM.scheduled_for_utc, NotificationORM.created_at)
    .limit(500)
)
```

The `order_by(scheduled_for_utc)` ensures oldest notifications are processed first when a backlog exists, preserving correct delivery order.

**Expected saving:** Eliminates ORM object spike during scheduler ticks. Caps per-tick allocation at 500 rows.

---

## Fix 6 — Stream daily precompute queries with `yield_per` instead of `fetchall`

**File:** `src/infra/services/daily_context_precompute_service.py` (lines ~454, ~470, ~498, ~515)

**Current:** 4 `fetchall()` queries per timezone batch — loads all active users' preferences, FCM tokens, profiles, and calories into 4 co-resident Python dicts simultaneously.

**Why this spikes:** For a timezone with many users, 4 large result sets live in RAM at the same time. With the largest timezone (`Asia/Ho_Chi_Minh`) this can be 50–100 MB.

**Change:** Replace all 4 `session.execute(...).fetchall()` calls with `yield_per(100)` streaming:

```python
# Before
rows = session.execute(text(...), params).fetchall()

# After
rows = list(session.execute(text(...).execution_options(yield_per=100), params))
```

Using `list()` preserves the existing dict-comprehension patterns downstream while streaming from the DB cursor in 100-row chunks rather than materialising all rows at once.

**Note:** SQLAlchemy Core `text()` queries support `.execution_options(yield_per=N)`. This buffers at most 100 rows at a time from the DB cursor, keeping peak RAM proportional to the batch size, not the total user count.

**Expected saving:** Peak memory per timezone batch drops from O(all users × 4 queries) to O(100 rows × sequential).

---

## Fix 7 — Explicit `gc.collect()` after scheduler batch runs

**File:** `src/infra/services/scheduled_notification_service.py` and `src/infra/services/daily_context_precompute_service.py`

**Why:** Python's garbage collector is generational and runs on object allocation thresholds, not time. After a large batch operation (sending 500 notifications or precomputing a large timezone batch), many objects become unreachable but are not immediately collected. The scheduler runs every 60s, meaning unreachable objects from one tick accumulate before GC clears them, contributing to the gradual memory creep.

**Change:** Add `import gc` and call `gc.collect()` at the end of each scheduler tick:

- In `scheduled_notification_service.py` — at the end of `_send_due_notifications()`
- In `daily_context_precompute_service.py` — at the end of each per-timezone `_precompute_for_timezone()` call

```python
import gc
# ... end of batch operation ...
gc.collect()
```

**Expected saving:** Reduces accumulation between ticks. Particularly effective when combined with Fix 5 and Fix 6 (smaller batches = more GC-friendly object lifecycle).

---

## Summary of Changes

| Fix | File(s) | Lines changed |
|-----|---------|---------------|
| 1 | `docker-entrypoint.sh`, `src/infra/database/config_async.py` | ~3 lines (workers default in both + 2 uvicorn flags) |
| 3 | `src/api/dependencies/auth_cache.py` | 1 line |
| 4 | `src/domain/services/meal_discovery/food_image_search_service.py` | 2 lines |
| 5 | `src/infra/repositories/notification/reminder_query_builder.py` | 1 line |
| 6 | `src/infra/services/daily_context_precompute_service.py` | ~4 lines |
| 7 | `scheduled_notification_service.py` + `daily_context_precompute_service.py` | ~4 lines |

**Total: ~15 lines of changes across 6 files.**

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Baseline RAM | ~1.6 GB (80%) | ~800 MB (40%) |
| Peak RAM (scheduler) | ~1.76 GB (82%) | ~900 MB (45%) |
| Gradual creep over 8h | +150 MB | ~0 (worker recycling) |
| Headroom before OOM | ~400 MB | ~1.1 GB |

## Non-Goals

- Fix 2 (image upload bounded read) — deferred, to be designed separately.
- Removing LangChain / Firebase dependencies — major refactor, separate initiative.
- Upgrading Render plan — not needed after these fixes.
