# Render Cron Notification Architecture

**Date**: 2026-05-21
**Status**: Approved

## Problem

The `ScheduledNotificationService` runs as an in-process asyncio loop (every 60s) inside the FastAPI web process on a 1 GB Render instance. This causes CPU spikes of ~80%, competing directly with request handling. The `ScheduledEmailService` currently only fires once at app startup — it is not a true recurring job.

## Goal

Move all scheduled notification work out of the web process into two dedicated Render Cron Job services:
- **Push cron**: create + dispatch FCM push notifications, every 2 minutes
- **Email cron**: send lifecycle emails daily at 09:00 UTC

The web service becomes a pure request handler with zero background loops.

---

## Architecture

### Infrastructure (render.yaml)

```
┌─────────────────────────────────────────────────────────┐
│  mealtrack-api (web)      — pure request handler        │
│  mealtrack-cron-push      — */2 * * * *                 │
│  mealtrack-cron-email     — 0 9 * * *                   │
└─────────────────────────────────────────────────────────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                   shared: Neon DB + Redis + Firebase
```

All three services use the same Docker image / build. Only the `startCommand` differs.

### Push Cron — Three Phases Per Run

Each run is a single-shot Python script that executes all three phases in sequence, then exits.

```
Phase 1 — Creation (meal reminders)
  Load distinct timezones from DB
  Detect which timezones are within 3 min of local midnight
  → DailyContextPrecomputeService.precompute_for_timezone()
  → INSERT NotificationORM rows (breakfast/lunch/dinner/daily_summary)
  Sentinel in Redis prevents double-creation within the same day

Phase 2 — Creation (trial expiry pushes)
  → ScheduledSubscriptionPushService.check_and_schedule_pushes()
  → INSERT trial T-2d / T-1d rows into notifications table
  UNIQUE CONSTRAINT prevents duplicate rows

Phase 3 — Dispatch
  → ReminderQueryBuilder.find_due_notifications() (scheduled_for_utc <= now, status=pending)
  → Claim rows (status → processing) to prevent double-send in concurrent runs
  → FCM batch send via Firebase
  → Mark rows sent / failed; deactivate invalid tokens
```

**Timing precision**: `NotificationORM` stores exact `scheduled_for_utc` timestamps. Dispatch reads all rows where `scheduled_for_utc <= now`. Max notification delay = cron interval = **2 minutes**. This is acceptable for meal reminders and is close to the current 60s in-process behavior.

**Concurrent run safety**: If a run exceeds 2 minutes, the next cron fires before it finishes. This is safe because:
- Phase 1/2: UNIQUE CONSTRAINT + Redis sentinel prevent duplicate inserts
- Phase 3: `status=processing` claim prevents double-sends
- Rows stuck in `processing` for >10 min are reclaimed by `PROCESSING_RECLAIM_AFTER`

### Email Cron — Single Phase Per Run

```
→ ScheduledEmailService.check_and_send_emails()
    Re-engagement:   trial users inactive 3+ days → send via Resend → log to email_log
    Trial expiring:  subscription expires in 2 days → send via Resend → log to email_log
    Dedup:           DUPLICATE_WINDOW_DAYS=7 prevents re-sending within 7 days
```

---

## Code Changes

### New files

**`src/cron/push.py`** — entry point for push cron
```
asyncio.run(main()):
  1. initialize_sentry()
  2. initialize_firebase()
  3. init Redis client
  4. create NEW DB engine instance (NullPool — do NOT reuse module-level engine from src/infra/database/config.py)
  5. SELECT 1 warm-up query (15s timeout; exit if Neon cold-starting)
  6. Phase 1: load timezones → midnight detection → precompute
  7. Phase 2: check_and_schedule_pushes
  8. Phase 3: find_due + FCM send + mark sent
  9. engine.dispose(); sentry_sdk.flush(timeout=5)
```

**`src/cron/email.py`** — entry point for email cron
```
asyncio.run(main()):
  1. initialize_sentry()
  2. create NEW async DB engine instance (NullPool — do NOT reuse module-level async_engine)
  3. SELECT 1 warm-up
  4. ScheduledEmailService.check_and_send_emails()
  5. await async_engine.dispose(); sentry_sdk.flush(timeout=5)
```

**`render.yaml`** — infrastructure as code

### Modified files

**`src/api/main.py`**
- REMOVE: `initialize_scheduled_notification_service()` call in lifespan
- REMOVE: `ScheduledEmailService` instantiation and call in lifespan
- REMOVE: `SCHEDULED_EMAIL_ENABLED` env var check
- KEEP: `app.state.trial_push_service` — see below

**`src/api/base_dependencies.py`**
- KEEP `ScheduledSubscriptionPushService` instantiated as a singleton
- It is NOT used for scheduling in the web process
- It IS used by the RevenueCat RENEWAL webhook to delete stale trial rows on upgrade
- Remove `ScheduledNotificationService` initialization

**`src/infra/services/daily_context_precompute_service.py`**
- Change midnight detection from `minute == 0` to `minute < 3`
- Allows 1 minute of Render scheduling jitter on a 2-minute cron

### Removed / Not Used

- `SchedulerLeaderLock` — not used in cron scripts (single process, no competing workers). The cron entry points call underlying services directly, bypassing `ScheduledNotificationService` and its lock entirely. The class itself can remain in the codebase but is no longer called from any startup path.
- `SCHEDULED_EMAIL_ENABLED` environment variable — no longer needed; email schedule is controlled by render.yaml cron definition

---

## Key Design Decisions

### Why not call underlying services from the cron via the web service's HTTP API?

The user chose a dedicated Render Cron service (separate process) over an HTTP endpoint approach. This ensures cron work is fully isolated from request handling — no shared CPU, no risk of a slow cron run blocking web requests.

### Why NullPool for cron DB connections?

The web service uses a persistent connection pool (up to 12 connections). A short-lived cron process that opens 12 connections and exits would leave them dangling until Neon times them out. Neon has a connection limit. NullPool opens exactly the connections needed and closes them immediately on `engine.dispose()`.

### Why keep ScheduledSubscriptionPushService in the web process?

The RevenueCat webhook at `POST /webhooks/revenuecat` deletes pending trial push rows when a user's subscription renews (`app.state.trial_push_service.delete_pending_trial_notifications(user_id)`). This delete must happen synchronously in the web process when the webhook fires — it cannot be deferred to the cron.

### Why `minute < 3` for midnight detection?

Render cron scheduling has ±1 minute of jitter. A 2-minute cron (`*/2`) fires at :00, :02, :04... If :00 fires at :01 due to jitter, `minute < 3` still catches it. If :00 fires at :02, it is caught by the :02 run. Using exactly `minute < 2` risks missing midnight if the :00 run fires late.

### Why 09:00 UTC for email?

09:00 UTC = 16:00 VN time (ICT/UTC+7), a reasonable afternoon send for the primary Vietnamese user base. Lifecycle emails (re-engagement, trial expiring) have good open rates in the afternoon.

---

## Timing Guarantee

```
User sets breakfast reminder: 07:00 AM (local)
DailyContextPrecomputeService creates row: scheduled_for_utc = 00:00 UTC (for UTC+7)

Cron runs at 00:00 UTC → dispatches row (0 min delay)
Cron runs at 00:02 UTC → row already sent, skipped

Worst case: reminder scheduled for 00:01 UTC
Cron ran at 00:00 (not due yet) → next run at 00:02 → dispatched 1 min late
```

Maximum observed delay: **2 minutes**. Guaranteed to never send early.

---

## Error Handling

| Failure | Behavior |
|---|---|
| Neon cold start (>15s) | Cron exits early, logs warning, Sentry alert. Next run (2 min) retries. |
| Redis unavailable | Skip Phase 1 sentinel check; rely on DB UNIQUE CONSTRAINT. Phase 3 dispatch uses generic daily summary message. |
| FCM error on individual token | Token deactivated if error is in `DEACTIVATABLE_FCM_ERRORS`. Other tokens in batch still send. |
| Cron run > 2 min (overlap) | Next run claims only unclaimed rows. No double-sends. |
| Cron crashes mid-Phase 3 | Rows stuck in `processing` reclaimed after 10 min by `PROCESSING_RECLAIM_AFTER`. |
| Resend email API error | Log error, skip user, continue. Next daily run retries (dedup window allows). |

---

## Environment Variables

Cron services share the same env vars as the web service with these additions/removals:

| Variable | Web | Push Cron | Email Cron |
|---|---|---|---|
| `DATABASE_URL` | ✓ | ✓ | ✓ |
| `REDIS_URL` | ✓ | ✓ | — |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✓ | ✓ | — |
| `RESEND_API_KEY` | ✓ | — | ✓ |
| `SENTRY_DSN` | ✓ | ✓ | ✓ |
| `SCHEDULED_EMAIL_ENABLED` | removed | — | — |

---

## Out of Scope

- Changing notification content or user preference logic
- Adding new notification types
- Changing email templates
- Per-user timezone-aware email send time (all emails send at 09:00 UTC regardless of user timezone)
