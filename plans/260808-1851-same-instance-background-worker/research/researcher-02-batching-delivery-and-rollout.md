# Batching / Delivery / Rollout Research

## Scope
Move the three cron paths into one bounded in-instance background worker:
- notification precompute / trial push / dispatch / cleanup
- lifecycle email / Resend
- affiliate outbox

Constraints assumed:
- same Render Standard web instance
- 2GB RAM / 1 CPU
- baseline CPU about 20%
- one Uvicorn worker per instance
- keep CPU under 85%
- durable restart
- no Celery, no new broker, no separate paid worker

## What the code already does

### 1) Notification push path is already split into four idempotent phases
- `src/cron/push.py:7-11` documents the phases: precompute, trial push, dispatch, cleanup.
- `src/cron/push.py:67-85` precomputes per timezone and calls `DailyContextPrecomputeService.precompute_for_timezone()` in a loop.
- `src/cron/push.py:94-103` schedules trial-expiry rows through `CronTrialPushService.check_and_schedule_pushes(now)`.
- `src/cron/push.py:113-118` dispatches due rows through `CronNotificationDispatchService._send_due_notifications(now)`.
- `src/cron/push.py:126-132` cleans up expired rows through `cleanup_expired_notifications()`.

### 2) Dispatch has a real claim/reclaim seam with ordering and skip-locked
- `src/infra/services/cron_notification_dispatch_service.py:54-61` first reclaims stale processing rows before claiming due rows.
- `src/infra/services/cron_notification_dispatch_service.py:222-248` claims rows with `scheduled_for_utc <= now`, `status in ('pending','processing-stale')`, ordered by `scheduled_for_utc, created_at`, and uses `with_for_update(skip_locked=True)`.
- `src/infra/services/cron_notification_dispatch_service.py:45-47` and `:57-59` define the stale-processing window as 10 minutes.
- `src/infra/services/cron_notification_dispatch_service.py:181-214` batches FCM sends by 500 tokens per call and distinguishes:
  - success -> mark sent
  - token-level failures -> deactivate those tokens
  - wholesale send failure -> requeue rows for retry

### 3) Trial push is write-side batching with DB-native dedupe
- `src/infra/services/cron_trial_push_service.py:52-83` fetches expiring subs, then batches preference/token fetches, then inserts rows in one write pass.
- `src/infra/services/cron_trial_push_service.py:85-141` does batched SQL lookups for preferences and FCM tokens.
- `src/infra/services/cron_trial_push_service.py:145-173` computes scheduled time and pins the dedupe date to the charge date.
- `src/infra/services/cron_trial_push_service.py:171-173` explicitly says repeated runs and the clamp cannot produce a second row for the same user.
- DB dedupe is backed by `migrations/versions/050_notification_optimization.py:37-45`, unique on `(user_id, notification_type, scheduled_date)`.

### 4) Lifecycle email is simple but currently unbatched per-row send
- `src/cron/email.py:57-65` constructs `ResendEmailAdapter`, renderer, service, and `CronLifecycleEmailService`.
- `src/infra/services/cron_lifecycle_email_service.py:53-72` selects inactive trial users.
- `src/infra/services/cron_lifecycle_email_service.py:74-94` selects expiring trials.
- `src/infra/services/cron_lifecycle_email_service.py:96-110` dedupes with a 7-day `EmailLog` window before sending.
- `src/infra/services/cron_lifecycle_email_service.py:112-145` sends one email at a time and logs each successful send.

### 5) Affiliate outbox already has an explicit claim/send/mark split
- `src/cron/affiliate_outbox.py:32-55` gates the cron behind `AFFILIATE_INTEGRATION_ENABLED`, dispatches rows, and disposes observability/DB in `finally`.
- `src/infra/services/affiliate_outbox_dispatch_service.py:16-37` claims one batch inside a DB transaction.
- `src/infra/services/affiliate_outbox_dispatch_service.py:37-76` sends rows one by one, then marks sent or failed in a separate transaction.
- `migrations/versions/20260610000001_add_affiliate_event_outbox.py:19-46` shows the durable outbox schema and `status,next_attempt_at` index.

### 6) Notification and outbox tables already have retry-friendly indexes
- `migrations/versions/20260609000006_add_normalized_read_indexes.py:23-31` adds a partial reclaim index for `notifications` where `status = 'processing'`.
- `migrations/versions/050_notification_optimization.py:42-49` adds `idx_notifications_due` and `idx_notifications_expires`.
- `migrations/versions/20260610000001_add_affiliate_event_outbox.py:41-46` adds a unique idempotency key plus `status,next_attempt_at` index.

### 7) Observability boundaries are already set up for cron exits
- `src/cron/push.py:48-62` and `src/cron/email.py:39-55` do DB warm-up, capture exceptions, and flush observability before returning on cold-start failure.
- `src/cron/push.py:140-142`, `src/cron/email.py:74-76`, and `src/cron/affiliate_outbox.py:52-55` dispose the DB and flush observability at exit.
- `docs/code-standards.md:134-142` says cron entrypoints should capture exceptions and flush observability before exit.

## Batching seams to reuse in one bounded worker

Ranked by leverage:

1. Notification dispatch loop
   - This is the only path with real row claiming, send fan-out, retry, and cleanup.
   - It already has natural batch boundaries: claim batch, token batch, hydration batch, FCM 500-token chunking.

2. Affiliate outbox batch claim
   - The job already claims a finite batch and has an explicit terminal-failure path.
   - It is the cleanest second job to fold into the same worker after notifications.

3. Trial push insert batch
   - It is write-heavy but bounded by expiring subscriptions, preferences, and FCM token lookups.
   - It should run after notification dispatch so trial rows generated in the same tick can be picked up only if due.

4. Lifecycle email
   - Lowest complexity, but still useful to batch user selection and send windows.
   - It is currently the least operationally coupled to the notification worker, so it can move last if schedule risk needs to be reduced.

## Exact transaction boundaries

### Notification dispatch
- Claim transaction: `src/infra/services/cron_notification_dispatch_service.py:234-248`
  - reads due rows with `FOR UPDATE SKIP LOCKED`
  - flips them to `processing`
  - flushes before returning
- Mark transaction: later in the same service, separate from the claim phase
  - this means send happens outside the claim transaction
  - failure between send and mark leaves rows in `processing` until reclaim window expires

### Trial push
- Single UoW around query + insert path: `src/infra/services/cron_trial_push_service.py:52-83`
- Insert dedupe relies on DB uniqueness, not application-level locks

### Lifecycle email
- Query and send are separated by per-user/per-email-type duplicate checks
- Logging happens after each successful send, in a separate UoW
- This creates a small duplicate-send window if the process dies after send but before log insert

### Affiliate outbox
- Claim happens inside one transaction, send outside it, mark inside another transaction
- This is the classic durable outbox pattern
- Remaining risk is duplicate delivery on crash after external send but before mark-sent

## Duplicate / loss windows

### Notification dispatch
- Duplicate risk:
  - crash after external FCM send, before mark-sent
  - stale rows get reclaimed after 10 minutes, so duplicates are possible, but bounded
- Loss risk:
  - wholesale FCM failure path is handled by retrying rows rather than marking sent
  - token-level failures are handled by token deactivation
- Net: bounded duplicate window, low loss risk

### Trial push
- Duplicate risk:
  - repeated cron runs are suppressed by the unique `(user_id, notification_type, scheduled_date)` key
- Loss risk:
  - if the worker dies before insert commit, the row is simply absent and will be re-evaluated on next run
- Net: best of the three from an idempotency standpoint

### Lifecycle email
- Duplicate risk:
  - send succeeds, log write fails, next run resends after the 7-day window check misses the missing log
  - if two workers overlap, the current code has no DB claim lock
- Loss risk:
  - an exception before send just skips that user and advances the rest of the run
- Net: highest duplicate risk, because dedupe is read-side only

### Affiliate outbox
- Duplicate risk:
  - same as any outbox: external send succeeds, mark-sent fails, row replays
- Loss risk:
  - low, because rows stay pending/failed until retried or terminally failed
- Net: durable enough for the worker consolidation

## Tests to add or tighten

### Notification dispatch
- Claim ordering and skip-locked coverage:
  - assert rows are returned in `scheduled_for_utc, created_at` order
  - assert locked rows are skipped and reclaimed rows re-enter after timeout
- Send batching:
  - chunk boundary at 500 tokens
  - wholesale failure keeps rows retryable
  - token-level failures deactivate only the failed tokens

### Trial push
- Dedup:
  - repeated runs do not create duplicate rows for same user/date/type
- Boundary:
  - conversions within the lead window are clamped correctly
  - rows are not created for already-converted subs

### Lifecycle email
- Duplicate suppression:
  - recent `EmailLog` prevents resend
  - missing log after send remains a known loss/duplicate risk
- Selection:
  - inactive-trial and expiring-trial query windows stay stable

### Affiliate outbox
- Claim/mark flow:
  - rows are claimed once per batch
  - transient send failures stay retryable
  - terminal failures increment the permanent-failure path

### Cross-cutting
- Add one integration test for the single-worker scheduler loop:
  - all jobs run in sequence
  - one job failure does not stop the rest
  - observability flush still happens on exit

## Initial worker settings

Recommended starting batch sizes for the bounded worker:

| Job | Start | Why |
|---|---:|---|
| Notification claim batch | 100 rows | enough parallelism, still small enough for 2GB / 1CPU |
| FCM token chunk | 500 tokens | matches current code |
| Trial push insert batch | 100 users per loop | keeps query and insert cost bounded |
| Lifecycle email batch | 50 users per loop | email send is slower and more failure-prone |
| Affiliate outbox batch | 50 rows | matches current default |

If CPU rises above 85%:
- first shrink notification claim batch
- then shrink trial/email batch sizes
- leave FCM token chunk at 500 unless Firebase rejects the payload size

## Safe cron cutover

Ranked rollout order:

1. Add the in-instance worker in shadow mode
   - run it on the same instance but keep the existing Render crons enabled
   - log-only for the first pass on lifecycle email and affiliate outbox
   - compare row counts and runtime against the cron jobs

2. Move notification dispatch first
   - it already has the strongest claim/reclaim semantics
   - it also gives the biggest operational payoff because it owns precompute, trial, dispatch, and cleanup

3. Move affiliate outbox second
   - durable pattern, finite batch, easy to observe

4. Move trial push third
   - safe because DB uniqueness already prevents duplication

5. Move lifecycle email last
   - highest duplicate-risk path; keep old cron live until the worker proves stable

Cutover rules:
- keep old Render cron definitions intact until the worker has survived multiple scheduled windows
- disable one external cron at a time
- verify each job’s last-success timestamp and row counts before removing the old schedule
- retain the stale-processing reclaim window during and after cutover
- do not change claim ordering and duplicate semantics in the same rollout as the scheduler move

## Recommended architecture

Best choice:
1. One in-instance bounded scheduler loop on the existing web service
2. Notification worker first, affiliate outbox second, trial push third, lifecycle email last
3. Keep external crons only as temporary failback

Why this ranks first:
- lowest operational surface area
- no new broker or paid worker
- reuses existing DB-based idempotency
- keeps the duplicate window bounded and explicit
- fits the current repo’s cron/observability patterns

Rejected / lower-ranked:
- Celery or new queue broker: too much new infra for the stated constraint set
- Separate paid worker: violates the budget and instance constraint
- Pure external-cron-only consolidation: does not remove the split operational surface, only renames it

## Evidence gaps / limitations

- I did not run a live load test in this session.
- I did not inspect every test file around cron behavior because the repo already exposes the key claim semantics in code and migrations.
- I did not browse external docs because the main plan can be derived from the repo and the user-supplied infrastructure constraints.

## Next steps

1. Add the bounded worker loop and feature flag controls.
2. Add or tighten the tests listed above.
3. Run a focused load test against the claim/send loops.
4. Cut over notification dispatch first, then outbox, then trial push, then lifecycle email.

**Status:** DONE
**Summary:** Mapped the existing cron paths, claim semantics, dedupe windows, and rollout order for consolidating them into one bounded in-instance worker.
**Concerns:** Lifecycle email still has the highest duplicate window; I recommend keeping its external cron as fallback until the new worker proves stable.
