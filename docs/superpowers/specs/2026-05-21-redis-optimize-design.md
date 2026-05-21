# Redis Command Optimization

**Date:** 2026-05-21  
**Branch:** `feature/redis-optimize` (from `delivery`)  
**Problem:** Upstash free tier limit is 500K commands/month. With 10,000+ users, the daily notification precompute alone generates ~620K commands/month (10K users × 2 commands × 31 days), exceeding the entire budget before any user makes a request.

---

## Root Cause Analysis

At 1:37 PM snapshot (Upstash dashboard):

| Command | Count | Source |
|---|---|---|
| HSET | 4.4K | `DailyContextPrecomputeService.hset_batch()` |
| EXPIRE | 4.4K | Same — paired with every HSET |
| GET | 4.7K | Auth UID lookup + all query handler caches |
| HGETALL | 2.3K | `ScheduledNotificationService` — every tick |
| SETEX | 1.4K | Nutrition lookup + standard SET ops |
| DEL | 1.1K | Meal mutation cache invalidations |
| KEYS | 125 | `delete_pattern()` — blocking, not SCAN |

HSET + EXPIRE + HGETALL + EXISTS = **~57% of all commands** from the notification system alone.

**Secondary bug:** Redis hashes are written for ALL users with notification preferences, including users with no active FCM token (no app installed). The FCM filter only applies when inserting notification rows, not when writing hashes.

---

## Solution

Two changes combined:

- **Option A:** Eliminate the Redis hash system from the notification pipeline entirely. Replace with a PostgreSQL batch query for real-time `calories_consumed` at send time, and an in-memory sentinel set for precompute deduplication.
- **Option B:** Replace Redis auth UID caching with a process-level `TTLCache`. Zero Redis commands for every authenticated request.

Minor additions: extend two short TTLs, fix `KEYS` → `SCAN` in `delete_pattern()`.

---

## Option A: Notification Pipeline — No More Redis Hashes

### Eligibility Filter (SQL level)

The precompute currently fetches every user with notification preferences, then discards those without FCM tokens in Python. Move the filter to SQL via `EXISTS` on `user_fcm_tokens`:

```sql
FROM notification_preferences np
JOIN users u ON u.id = np.user_id
WHERE u.is_active = true
  AND np.is_deleted = false
  AND EXISTS (
      SELECT 1 FROM user_fcm_tokens t
      WHERE t.user_id = np.user_id AND t.is_active = true
  )
```

Users with no app installed are excluded before any computation. At typical mobile app retention rates, this alone reduces the eligible user set by 50–70%.

### Remove Redis Hash Write from Precompute

`DailyContextPrecomputeService._precompute_db_sync()` currently returns a list of `(redis_key, mapping, ttl)` tuples that are batch-written to Redis as hashes. These hashes store: `calorie_goal`, `calories_consumed`, `gender`, `language_code`.

This data is already written to the `notifications.context` JSONB column in the same DB transaction. The Redis hash is a redundant copy.

**Change:** Remove the "Build Redis items" section (the final loop in `_precompute_db_sync`). The function returns nothing (or a count). The `precompute_for_timezone` method no longer calls `hset_batch`.

### Replace HGETALL with PG Batch Query at Send Time

`ScheduledNotificationService._send_due_notifications()` currently:
1. Fetches due notification rows from PG (which already contain `calorie_goal`, `gender`, `language_code`, `fcm_tokens` in JSONB `context`)
2. Calls `hgetall_batch()` to get a fresher `calories_consumed` from Redis for meal reminders

**Change:** Replace step 2 with a direct PG batch query — the same query already in `_precompute_db_sync`:

```python
async def _fetch_calories_consumed_batch(
    user_ids: list[str], now: datetime
) -> dict[str, int]:
    """Batch-fetch today's consumed calories per user from DB.

    Due notifications can span multiple user timezones. Rather than computing
    per-user UTC day boundaries (which requires joining users.timezone and doing
    timezone math per row), we use a 24-hour lookback from now. Meal reminders
    fire mid-day locally, so a 24-hour window captures all of the user's current
    day meals. This is equivalent in accuracy to the previous Redis hash, which
    was already hours stale from the midnight precompute.
    """
    window_start = now - timedelta(hours=24)

    def _sync():
        with UnitOfWork() as uow:
            rows = uow.session.execute(text("""
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
            """), {"ids": user_ids, "start": window_start}).fetchall()
        return {row.user_id: int(round(row.consumed_calories)) for row in rows}
    return await asyncio.to_thread(_sync)
```

This is real-time data — more accurate than the Redis hash (which was hours stale from the midnight precompute). The DB round-trip only happens when there are due notifications (not every tick).

### Replace Redis Sentinel with In-Memory Set

The sentinel key `precomputed:{date}:{tz}` prevents double-running the precompute for the same `(date, timezone)`. Since the scheduler is single-leader (enforced by `SchedulerLeaderLock`), a module-level set is authoritative:

```python
# In DailyContextPrecomputeService
_precomputed_today: set[tuple[str, str]] = set()  # (date_isoformat, tz_name)
```

`is_precomputed()` checks the set. On positive result from `precompute_for_timezone()`, add to set. On process restart, the set is empty — startup catch-up reruns as before. The `notifications` INSERT uses `ON CONFLICT DO NOTHING`, so reruns are idempotent.

### Remove Redis Dependency from DailyContextPrecomputeService

`DailyContextPrecomputeService.__init__` currently takes `redis_client: RedisClient`. After this change it takes no Redis dependency — only `UnitOfWork` (via sync threads). Update the constructor in `ScheduledNotificationService` accordingly.

Methods to remove from `RedisClient` (or keep unused — do not delete if other callers exist): `hset_batch`, `hgetall_batch`. Verify no other callers before removing.

---

## Option B: In-Memory Auth UID Cache

### Change

Replace Redis GET/SET for `auth:uid:{firebase_uid}` with a `cachetools.TTLCache` at module level in `src/api/dependencies/auth_cache.py`:

```python
from cachetools import TTLCache

_uid_cache: TTLCache[str, dict] = TTLCache(maxsize=15_000, ttl=600)  # 10 min
```

**`get_cached_user_id`:** check `_uid_cache.get(firebase_uid)` first; skip Redis entirely.  
**`set_cached_user_id`:** write to `_uid_cache[firebase_uid]`; skip Redis entirely.  
**`invalidate_cached_user_id`:** `_uid_cache.pop(firebase_uid, None)`; already called on user deletion — correctness preserved.

The Redis cache key `auth:uid:{firebase_uid}` and its TTL definition in `CacheKeys.auth_uid_to_user()` can remain but will no longer be written. The `CachePort` injection in `get_cached_user_id` / `set_cached_user_id` becomes unused for auth; pass `None` or leave for future use.

### Dependency

Add `cachetools` to `requirements.txt`. Not currently present.

### Caveat

In-memory cache is per-process. Multiple Render instances each maintain their own cache. A cold process gets one extra DB query per unique user on first request — not a correctness issue. With a single Render instance (current setup) this is transparent.

---

## Minor: TTL Extensions

In `src/domain/cache/cache_keys.py`:

| Key | Current TTL | New TTL |
|---|---|---|
| `user:{user_id}:daily_breakdown:{week_start}` | 300 s (5 min) | 1800 s (30 min) |
| `user:{user_id}:weekly_budget:{week_start}` | 600 s (10 min) | 1800 s (30 min) |

Both keys are invalidated correctly on meal mutation and metric update via `cache_invalidation_event_handler.py` and `update_user_metrics_command_handler.py`. TTL only matters for stale-read windows during the gap before mutation — 30 minutes is acceptable for budget/breakdown data.

---

## Minor: KEYS → SCAN

In `src/infra/cache/redis_client.py`, `delete_pattern()` uses `KEYS` (blocking, scans entire keyspace). Replace with an async `SCAN` loop:

```python
async def delete_pattern(self, pattern: str) -> int:
    deleted = 0
    async for key in self.client.scan_iter(pattern):
        await self.client.delete(key)
        deleted += 1
    return deleted
```

Prevents Redis blocking on large keyspaces. No behavioral change.

---

## Files Changed

| File | Change |
|---|---|
| `src/infra/services/daily_context_precompute_service.py` | Remove Redis dep, add in-memory sentinel set, add FCM eligibility filter to Query 1, remove Redis hash build |
| `src/infra/services/scheduled_notification_service.py` | Remove `hgetall_batch` call, add `_fetch_calories_consumed_batch` PG helper, update `DailyContextPrecomputeService` constructor call |
| `src/api/dependencies/auth_cache.py` | Add `TTLCache`, replace Redis GET/SET/DEL with in-memory ops |
| `src/infra/cache/redis_client.py` | Fix `delete_pattern()` KEYS→SCAN; optionally remove `hset_batch`/`hgetall_batch` if no other callers |
| `src/domain/cache/cache_keys.py` | Extend `daily_breakdown` and `weekly_budget` TTLs |
| `requirements.txt` | Add `cachetools` |

---

## Projected Impact

At 10,000 users, ~40% with active FCM tokens (4,000 eligible):

| Change | Commands Saved/Month |
|---|---|
| Remove HSET + EXPIRE (precompute) | ~248K (was 620K, now 0) |
| Remove HGETALL (send-time) | Significant — scales with notification volume |
| Remove EXISTS + SET (sentinel) | ~30K |
| Remove auth GET/SET | High — one per authenticated request |
| **Net** | **Well under 500K/month** |

The precompute change alone brings the budget from >620K to 0 for the hash system. Combined with auth cache elimination, total monthly commands should land in the 100–200K range depending on active user request volume.

---

## What Does Not Change

- All query caches (TDEE, profile, macros, weekly budget, streak, activities) remain in Redis — low write frequency, high read value.
- Nutrition lookup cache remains in Redis — write-once, 24h TTL, high reuse.
- Food search / food detail cache remains in Redis — 7-day TTL.
- Meal suggestion session hashes remain in Redis — short-lived, per-user.
- Notification sending logic, FCM batch send, leader lock — unchanged.
- No database migrations required.
