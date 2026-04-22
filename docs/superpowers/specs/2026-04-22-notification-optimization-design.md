---
status: approved
created: 2026-04-22
branch: delivery
---

# Notification System Optimization — System Design

## Problem

Current scheduler processes 1,000 users sequentially: 4 DB queries per user (profile, TDEE, weekly budget, adjusted daily) plus 1 FCM API call per user. At 10,000 users this hits ~40,000 queries per batch. At 100,000 users the DB dies.

**Target:** 6 batch queries (pre-compute, once per timezone group per day) + 3 queries per send tick + 1–2 FCM calls.

---

## Final Architecture Decisions

| Component | Storage | Rationale |
|---|---|---|
| `user_daily_context` | **Redis** | TTL auto-expires, no cleanup job, fast hash lookup, already in stack |
| `notifications` | **PostgreSQL JSONB** | Queryable by `scheduled_for_utc`, UNIQUE dedup, ACID, audit trail |
| `notification_preferences` | PostgreSQL (unchanged) | Timezone filter JOIN, user settings |
| `user_fcm_token` | PostgreSQL (unchanged) | FK integrity, multi-device per user |
| `notification_sent_log` | **DROPPED** | `notifications.status` + UNIQUE constraint replaces it |

---

## System Flow

```
60s scheduler loop
│
├─ Phase 1: Lookahead (30 min before first reminder per timezone group)
│   IF sentinel key precomputed:{date}:{offset} missing from Redis:
│     → 5 SQL batch queries + 1 Redis pipeline → write context to Redis
│     → 1 SQL batch INSERT → create notification rows for the day
│     → SET sentinel key precomputed:{date}:{offset} TTL 25h
│
└─ Phase 2: Send
    → 1 SQL query  (fetch due notifications from PostgreSQL — includes stable context)
    → 1 Redis pipeline  (HGET calories_consumed for each due user)
    → Python: remaining = calorie_goal - calories_consumed
    → 1–2 FCM batch calls
    → 1 SQL update  (mark sent)
```

---

## Storage Schemas

### Redis — `user_daily_context:{user_id}` (Hash)

```
Key:    user_daily_context:{user_id}
TTL:    86400 seconds (24 hours — auto-expires, no cleanup needed)

Fields:
  calorie_goal         integer   — computed from TDEE + weekly budget adjustment
  calories_consumed    integer   — SUM of today's meals at pre-compute time (~30 min before first reminder)
  gender               string    — male / female
  language_code        string    — en / vi
  utc_offset_minutes   integer   — user's UTC offset in minutes
  context_date         string    — YYYY-MM-DD, used to detect stale cache on restart
```

Staleness: `calories_consumed` is ~30 minutes stale at send time. Acceptable for meal reminders — this is a reminder, not a real-time tracker.

Fallback: if key missing at send time (Redis eviction, restart), fall back to on-demand per-user SQL calculation (current code path).

### PostgreSQL — `notifications` table (JSONB)

```sql
CREATE TABLE notifications (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(30) NOT NULL,
    scheduled_date    DATE        NOT NULL,
    scheduled_for_utc TIMESTAMPTZ NOT NULL,
    status            VARCHAR(10) NOT NULL DEFAULT 'pending',  -- pending/sent/failed
    context           JSONB       NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ NOT NULL,                    -- scheduled_date + 7 days

    CONSTRAINT uq_notification_per_user_type_date
        UNIQUE (user_id, notification_type, scheduled_date)
);

CREATE INDEX idx_notifications_due
    ON notifications (scheduled_for_utc, status)
    WHERE status = 'pending';

CREATE INDEX idx_notifications_expires
    ON notifications (expires_at)
    WHERE status != 'pending';
```

`context` JSONB shape:
```json
{
  "fcm_tokens": ["token_abc...", "token_def..."],
  "calorie_goal": 1800,
  "gender": "male",
  "language_code": "vi"
}
```

`calories_consumed` is NOT stored in the notification context — it is read from Redis at send time so it reflects the pre-computed value from that morning's batch.

---

## Pre-compute Service

**Trigger:** The 60s scheduler detects that a timezone group's earliest reminder time is 25–35 minutes away AND the sentinel key `precomputed:{today}:{utc_offset_minutes}` is absent from Redis. The sentinel key is set after a successful pre-compute with TTL 25h — this prevents re-running on every loop tick.

**Steps (all batch, no per-user loops):**

```
1. SELECT np.user_id, np.*_time_minutes, np.*_enabled, t.fcm_token
   FROM notification_preferences np
   JOIN user_fcm_tokens t ON t.user_id = np.user_id AND t.is_active = true
   JOIN users u ON u.id = np.user_id
   WHERE u.utc_offset_minutes = :offset
   [1 query — all users in this timezone group with their tokens]

2. SELECT * FROM user_profiles WHERE user_id IN (:user_ids)
   [1 query]

3. SELECT * FROM weekly_budgets
   WHERE user_id IN (:user_ids) AND week_start = :monday
   [1 query]

4. Python: for each user:
       tdee = TdeeCalculationService.calculate(profile)
       effective = WeeklyBudgetService.get_effective_adjusted_daily(budget, tdee, ...)
       calorie_goal = effective.adjusted.calories
   [CPU only — no DB]

5. SELECT user_id, COALESCE(SUM(calories), 0) as consumed
   FROM meals
   WHERE local_date = :today AND user_id IN (:user_ids)
   GROUP BY user_id
   [1 query]

6. Redis pipeline: HSET user_daily_context:{user_id} ... / EXPIRE 86400
   For each user (pipelined, single round-trip)
   [1 Redis pipeline]

7. INSERT INTO notifications (batch, all reminder types for the day)
   ON CONFLICT (user_id, notification_type, scheduled_date) DO NOTHING
   [1 SQL query — idempotent, safe to re-run on restart]

Total: 5 SQL queries + 1 Redis pipeline — for the entire timezone group.
Runs once per timezone group per day.
```

`scheduled_for_utc` per notification is computed as:

```python
scheduled_for_utc = today_utc_midnight + timedelta(minutes=reminder_time_minutes - utc_offset_minutes)
```

---

## Scheduler Send Loop

```python
async def _send_due_notifications(self, now: datetime):

    # 1. Fetch all due notifications (1 query)
    due = db.query(Notification).filter(
        Notification.scheduled_for_utc.between(now, now + timedelta(minutes=1)),
        Notification.status == 'pending'
    ).all()

    if not due:
        return

    # 2. Batch-fetch Redis context for all due users (1 pipeline)
    contexts = redis.pipeline()
    for n in due:
        contexts.hgetall(f"user_daily_context:{n.user_id}")
    contexts = contexts.execute()

    # 3. Render messages in Python (CPU only)
    for notif, ctx in zip(due, contexts):
        if not ctx:
            ctx = await self._fallback_compute(notif.user_id)  # on-demand if Redis miss
        remaining = int(ctx['calorie_goal']) - int(ctx['calories_consumed'])
        notif._title, notif._body = render_message(
            notif.notification_type, remaining,
            notif.context['gender'], notif.context['language_code']
        )
        notif._tokens = notif.context['fcm_tokens']

    # 4. Group by (title, body) → batch FCM (500 tokens/call)
    groups = defaultdict(list)
    for notif in due:
        groups[(notif._title, notif._body)].extend(notif._tokens)

    for (title, body), tokens in groups.items():
        for chunk in chunked(tokens, 500):
            firebase_service.send_multicast(tokens=chunk, title=title, body=body)

    # 5. Mark sent (1 query)
    db.query(Notification).filter(
        Notification.id.in_([n.id for n in due])
    ).update({'status': 'sent'})
```

---

## FCM Batching Reality

| Type | Message | Batching efficiency |
|---|---|---|
| Breakfast | Static body | ✅ All users → 1–2 FCM calls |
| Daily summary | 5 categories × 2 langs × 2 genders = 20 variants | ✅ Groups well |
| Lunch / Dinner | `{remaining}` is unique per user | ⚠️ Limited — 1 call per unique value |

**Future improvement (out of scope):** Move `remaining` to FCM `data` payload; mobile renders it. All lunch tokens collapse to 1–2 FCM calls. Requires mobile-side change.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Pre-compute fails | Fallback: on-demand per-user SQL calc at send time (current `_get_user_context` path) |
| Redis key missing at send time | Same fallback — on-demand calc, notification still goes out |
| Notification row already exists | `ON CONFLICT DO NOTHING` — idempotent, safe on restart |
| FCM token invalid | Deactivate token via existing `_handle_failed_tokens()` |
| Send fails | `status = 'failed'`, no retry — meal reminders are fire-and-forget; user gets next scheduled reminder |
| User deleted | `ON DELETE CASCADE` removes notification rows automatically |
| Timezone offset changes | Redis TTL expires naturally; next pre-compute uses new offset |

---

## Migration

```sql
-- Up (single migration: 050_notification_optimization.py)
CREATE TABLE notifications (...);          -- new job queue
DROP TABLE notification_sent_log;          -- replaced by notifications.status

-- No migration for user_daily_context — pure Redis, no SQL table
-- No migration for notification_preferences or user_fcm_token — unchanged

-- Down
DROP TABLE notifications;
CREATE TABLE notification_sent_log (...);
```

**Deployment gap:** `notifications` starts empty. Lookahead pre-compute fills it within 30 minutes of deployment. At most one 60s window of missed sends. Acceptable for a reminder system.

---

## Files to Create / Modify

| Action | Path |
|---|---|
| CREATE | `src/infra/database/models/notification/notification.py` |
| CREATE | `src/infra/services/daily_context_precompute_service.py` |
| CREATE | `migrations/versions/050_notification_optimization.py` |
| MODIFY | `src/infra/services/scheduled_notification_service.py` |
| MODIFY | `src/infra/repositories/notification/reminder_query_builder.py` |
| MODIFY | `src/infra/services/firebase_service.py` — add `send_multicast()` |
| MODIFY | `src/domain/services/notification_service.py` — remove dedup logic |
| DELETE | `src/infra/database/models/notification/notification_sent_log.py` |
| DELETE | `src/domain/ports/notification_dedup_port.py` |

---

## Performance Summary

| Metric | Current (10k users) | New (10k users) | New (100k users) |
|---|---|---|---|
| DB queries per batch | 4,001 | 3 (send) | 3 (send) |
| Pre-compute queries | 0 | 5 SQL + 1 Redis pipeline (once/day/group) | same |
| FCM calls | 1,000 | 2–10 (breakfast/summary batch well) | 20–100 |
| calories_consumed staleness | 0 | ~30 min | ~30 min |
| Processing time per batch | ~100s | <1s | <1s |

---

## Success Criteria

- [ ] Notification batch completes in <1s
- [ ] SQL queries at send time: 2 (fetch notifications + mark sent) + 1 Redis pipeline
- [ ] Pre-compute runs once per timezone group per day
- [ ] Redis cache hit rate >99% under normal operation
- [ ] Fallback fires correctly on Redis miss
- [ ] No duplicate notifications (UNIQUE constraint holds)
- [ ] `notification_sent_log` table removed
- [ ] All existing tests pass
