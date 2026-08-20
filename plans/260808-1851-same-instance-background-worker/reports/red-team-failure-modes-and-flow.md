# Red-Team Failure Modes and Flow Review

## Scope

- Reviewed `plan.md`, Phases 1-5, and both research reports in full.
- Traced live flows from `docker-entrypoint.sh` through the push, lifecycle-email, and affiliate cron entrypoints; their services, UoWs/repositories, provider adapters, models, migrations, and health surfaces.
- Lenses: Failure Mode Analyst + Flow Tracer. Findings below preserve the approved same-instance, serial-worker, no-broker, bounded-batch, and resource-threshold decisions.
- Verdict: **not implementation-ready**. Four critical flow/control gaps and five high-risk correctness gaps need plan corrections before coding.

## Critical Findings

### F1. Push cutover disables trial scheduling and cleanup before their worker paths are enabled

- **Severity:** Critical — permanent missed customer notifications during rollout.
- **Plan location:** `phase-05-verification-and-staged-cron-cutover.md:63-65` enables dispatch/precompute and disables the push cron in step 6, but does not enable trial reminders until step 8. `phase-05-verification-and-staged-cron-cutover.md:22` says each stage must enable its worker path before disabling the matching cron.
- **Repository evidence:** The one push cron owns all four phases: precompute at `src/cron/push.py:67-86`, trial scheduling at `src/cron/push.py:94-103`, dispatch at `src/cron/push.py:111-118`, and cleanup at `src/cron/push.py:126-132`. Trial selection only considers active subscriptions expiring in the future window at `src/infra/services/cron_trial_push_service.py:52-83` and `src/infra/repositories/subscription_repository_async.py:91-110`.
- **Failure flow:**
  1. Enable only worker dispatch/precompute.
  2. Disable the single Render push cron as step 6 directs.
  3. Trial scheduling and cleanup stop because they are not separate cron services.
  4. A subscription enters and leaves the one-day expiry window before step 8.
  5. No trial notification row is ever inserted; later execution cannot recover it because the subscription is no longer eligible.
- **Minimal correction:** Either enable all four push sub-workloads before disabling the monolithic cron, or first add per-phase compatibility-cron flags so trial/cleanup remain active while dispatch/precompute move. Make the rollout table name the executor for every push sub-phase at every stage.

### F2. The rollback procedure requires per-workload flags that no phase defines

- **Severity:** Critical — rollback of one workload can stop or duplicate unrelated workloads.
- **Plan location:** `phase-01-durable-runtime-foundation.md:63` defines only global worker enabled/shadow settings. `phase-05-verification-and-staged-cron-cutover.md:63-66` requires independent workload cutovers, and line 66 says to disable “its worker flag” during each rollback drill.
- **Repository evidence:** Push and email run unconditionally once invoked (`src/cron/push.py:43-46`, `src/cron/email.py:34-37`). Affiliate has only the business integration gate `AFFILIATE_INTEGRATION_ENABLED` at `src/cron/affiliate_outbox.py:32-34`; it is not an executor-selection flag. Push also combines four workloads in one module (`src/cron/push.py:67-132`).
- **Failure flow:**
  1. Push and affiliate are already cut over successfully.
  2. Lifecycle email fails its observation gate.
  3. Operators attempt the prescribed email-only worker rollback.
  4. Only a global worker flag exists: disabling it also stops push and affiliate; leaving it on lets email continue claiming while its cron is re-enabled.
  5. Rollback either creates outages/backlogs in healthy workloads or creates competing email executors.
- **Minimal correction:** Define explicit worker-execution flags for each independently staged workload, including the four push sub-phases or an explicitly atomic push group. Separate these from business/provider enable flags. Add disabled/enabled matrix tests and exact rollback ordering to Phase 4/5.

### F3. Notification ownership cannot be implemented safely with the current schema, and current “staleness” is based on schedule time

- **Severity:** Critical — active duplicate sends under backlog, cron overlap, or deploy overlap.
- **Plan location:** `phase-02-bound-notification-workloads.md:65` requires an owner token for sent/retry/failed mutations, but its related files at lines 42-59 include neither a notification model change nor a migration. Line 68 promises safe cron/worker overlap.
- **Repository evidence:** `NotificationORM` has status but no `owner_token`, `claimed_at`, or claim expiry at `src/infra/database/models/notification/notification.py:34-45`. Claim/reclaim decides that a processing row is stale from `scheduled_for_utc`, not claim time, at `src/infra/services/cron_notification_dispatch_service.py:222-248`; the recovery update repeats the same defect at lines 294-310. The existing reclaim index is likewise on `scheduled_for_utc` at `src/infra/database/models/notification/notification.py:71-75`.
- **Failure flow:**
  1. A notification scheduled an hour ago is claimed now and committed as `processing`.
  2. Provider I/O begins outside the transaction.
  3. A second cron/worker starts. Because the schedule time is already more than ten minutes old, it treats the actively claimed row as stale immediately.
  4. The second process resets/reclaims and sends the same notification while the first send is still active.
  5. There is no persisted owner with which either completion update can fence the other.
- **Minimal correction:** Add a notification ownership migration/model change: opaque owner token plus `claimed_at`/`claim_expires_at`; claim in one atomic statement; make every result mutation owner-conditional; reclaim only by claim expiry; replace the processing reclaim index accordingly. Add current/new and mixed-version claimant tests.

### F4. Auxiliary-worker failure is designed to kill the primary web service, contradicting the availability gate

- **Severity:** Critical — a worker-only defect can put the single web instance into a crash loop.
- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:41` and line 67 require the container to terminate if either child exits. Line 91 delegates repeated restart behavior to Render. This conflicts with `phase-05-verification-and-staged-cron-cutover.md:84`, which requires the web service to remain available through a worker crash.
- **Repository evidence:** Today the entrypoint `exec`s Uvicorn as the sole primary process at `docker-entrypoint.sh:34-42`. Worker dependencies can fail independently: Firebase initialization re-raises at `src/infra/services/firebase_service.py:38-60`, and async-engine import failure leaves the engine/session factory unavailable at `src/infra/database/config_async.py:126-133`.
- **Failure flow:**
  1. A worker-only credential/config/import defect makes the worker child exit at startup.
  2. The proposed supervisor terminates healthy Uvicorn and exits non-zero.
  3. Render restarts the same image with the same configuration.
  4. The worker exits again; the supervisor kills Uvicorn again.
  5. The only web instance is unavailable even though the API itself could serve traffic.
- **Minimal correction:** Treat Uvicorn as primary and the worker as restartable auxiliary: restart the worker in-container with bounded exponential backoff and a failure budget while persisting unhealthy heartbeat/alerts. Uvicorn death should still terminate the container. If the worker exceeds its failure budget, keep web serving and fail worker health loudly rather than unconditionally crash-looping the API.

## High-Priority Findings

### F5. Cleanup can delete a notification while its provider call is in flight

- **Severity:** High — externally delivered work loses its durable result/retry record.
- **Plan location:** `phase-02-bound-notification-workloads.md:67` only requires bounded cleanup; it does not exclude live claims. `phase-04-sibling-worker-and-process-supervision.md:62-63` schedules bounded steps independently.
- **Repository evidence:** Dispatch commits/returns claimed rows before provider work at `src/infra/services/cron_notification_dispatch_service.py:222-248`, sends outside that transaction at lines 181-215, then marks at lines 216-218. Cleanup deletes every expired row regardless of status/ownership at lines 287-292.
- **Failure flow:**
  1. An expired/backlogged row is claimed by worker A and its FCM request starts.
  2. Worker B or the compatibility cron runs cleanup concurrently.
  3. Cleanup deletes the `processing` row.
  4. FCM accepts the send; worker A’s owner-checked completion updates zero rows.
  5. Delivery occurred but durable state and duplicate diagnosis are gone.
- **Minimal correction:** Do not claim already expired rows. Restrict cleanup to terminal/pending rows, or to processing rows whose claim lease has expired; never delete a live owned claim. Add a concurrent claim/send/cleanup PostgreSQL test.

### F6. Renewing only between bounded steps still permits lease expiry and active split-brain execution

- **Severity:** High — two deploy generations can actively execute the same workload.
- **Plan location:** `phase-01-durable-runtime-foundation.md:64` validates only `lease TTL > renewal interval`; line 85 and `phase-04-sibling-worker-and-process-supervision.md:63` renew only between batches/steps. No upper bound ties TTL to provider-call or step duration.
- **Repository evidence:** Affiliate currently sends a claimed batch sequentially at `src/infra/services/affiliate_outbox_dispatch_service.py:37-63`; each call may consume the configured 10 seconds (`src/infra/adapters/affiliate_service_adapter.py:104-111`, `src/infra/config/settings.py:319-322`). Lifecycle email also iterates recipients serially at `src/infra/services/cron_lifecycle_email_service.py:35-46`, and Resend’s thread call has no explicit timeout at `src/infra/adapters/resend_email_adapter.py:42-52`. FCM performs blocking provider calls at `src/infra/services/firebase_service.py:172-173`.
- **Failure flow:**
  1. TTL=30s and renew interval=10s pass validation.
  2. A bounded affiliate/email/FCM step runs longer than 30s because of sequential calls or a stalled SDK call.
  3. The global lease expires while the old worker is still executing.
  4. A new deploy acquires the lease and reclaims expired item ownership.
  5. Old and new workers call the provider concurrently; owner checks after I/O are too late to prevent the duplicate side effect.
- **Minimal correction:** Run lease heartbeat as an independent async coordination task during provider I/O; enforce explicit provider-call deadlines; require item-claim TTL to exceed the maximum single in-flight call; re-check fencing ownership before each subsequent sub-call. Test takeover during a deliberately slow provider call.

### F7. Strict priority plus yielding does not prevent starvation

- **Severity:** High — daily precompute, trial scheduling, or cleanup can miss their windows under a hot dispatch queue.
- **Plan location:** `phase-02-bound-notification-workloads.md:40` sets dispatch first, then trial, precompute, cleanup. `phase-04-sibling-worker-and-process-supervision.md:62-63` always selects one due workload by priority. The only mitigation is an undecided risk note (“cap ... or aging”) at line 92, despite fairness being a required test at line 69.
- **Repository evidence:** The existing cron deliberately runs precompute and trial before dispatch (`src/cron/push.py:67-118`) and cleanup afterward (`src/cron/push.py:126-132`). The current dispatch claim has no limit at `src/infra/services/cron_notification_dispatch_service.py:234-244`, showing why the planned cap is necessary but not sufficient for cross-workload fairness.
- **Failure flow:**
  1. More than 100 notifications become due during every dispatch batch/yield interval.
  2. Dispatch remains the highest-priority due workload forever.
  3. The scheduler yields, then selects dispatch again.
  4. Precompute/trial/cleanup never run; yielding protects the event loop but not lower-priority jobs.
  5. Notification rows are absent or stale despite the worker process appearing healthy.
- **Minimal correction:** Choose and specify one fairness algorithm now: e.g. a maximum consecutive dispatch-batch count plus deadline override for scheduled jobs. Persist/measure per-workload lag and add a test with an indefinitely replenished dispatch queue proving all scheduled workloads meet their SLA.

### F8. Local resource guards observe the wrong scope for a shared-container threshold

- **Severity:** High — the worker continues claiming after total container CPU/memory has crossed the approved threshold.
- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:29` correctly states process RSS is insufficient, but line 65 says to record worker-process metrics locally and use Render container metrics only for deployment decisions, while line 36 requires the runtime to pause above 85% CPU/memory.
- **Repository evidence:** Uvicorn is a separate OS process started at `docker-entrypoint.sh:38-42`; the proposed worker is a sibling, so worker-process RSS/CPU excludes the web child. Existing protected health metrics are process-local SQLAlchemy pool data at `src/api/routes/v1/health.py:94-117`, not container CPU/memory.
- **Failure flow:**
  1. Uvicorn consumes 80% CPU (or most of the 2 GB memory) under web load.
  2. The worker process itself reports only 10% CPU/modest RSS.
  3. The local guard sees a value below 85% and claims another batch.
  4. Combined use crosses the threshold and web latency/OOM risk returns.
  5. Render telemetry can diagnose the breach later but cannot act as the runtime brake promised by the plan.
- **Minimal correction:** Read container-scoped cgroup v2 CPU/memory counters for the guard, with worker RSS as diagnostic detail only. Test hysteresis with synthetic sibling-process pressure, not merely worker-process pressure.

### F9. The lifecycle-email refactor can silently replace the existing seven-day suppression with a daily key

- **Severity:** High — inactive users can receive re-engagement email every day.
- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:64` defines `lifecycle:{type}:{user_id}:{scheduled_date}` and skips only completed/currently owned keys. Line 65 retains `EmailLog` as history but does not explicitly retain the seven-day eligibility suppression, despite the compatibility requirement at line 36.
- **Repository evidence:** Inactive users remain candidates on every run at `src/infra/services/cron_lifecycle_email_service.py:53-72`. Today every candidate is filtered through `_has_recent_email` at lines 35-46, and that check uses a seven-day cutoff at lines 96-110.
- **Failure flow:**
  1. An inactive trial user is eligible on Monday; key `...:Monday` is completed.
  2. The user remains inactive on Tuesday.
  3. The date-based key is now different, so durable claim dedupe permits another send.
  4. If the refactor treats `EmailLog` only as audit history, the current seven-day suppression is gone.
  5. The worker sends daily re-engagement mail while all concurrency/idempotency tests still pass.
- **Minimal correction:** Explicitly preserve the seven-day business eligibility check before atomic claim creation (or encode a stable suppression-window key). Test consecutive daily schedule keys for the same inactive user and assert only one send in seven days.

### F10. User-ID keyset pagination has no snapshot boundary for users who become eligible behind the cursor

- **Severity:** High — a partial daily run can complete while omitting newly eligible users.
- **Plan location:** `phase-02-bound-notification-workloads.md:32-34` treats stable user-ID keyset pagination plus a durable cursor as sufficient; lines 63-64 do not define snapshot membership or an eligibility watermark.
- **Repository evidence:** User IDs are random UUID strings at `src/infra/database/models/base.py:10-21`, not monotonic creation IDs. Current precompute eligibility depends on timezone/preferences and existence of an active FCM token at `src/infra/services/daily_context_precompute_service.py:472-514`. Registering a first token only reschedules if timezone changed at `src/app/handlers/command_handlers/register_fcm_token_command_handler.py:75-99`; unchanged timezone skips rescheduling. The user table has `timezone` alone, not a `(timezone,id)` batching index, at `src/infra/database/models/user/user.py:56-62`.
- **Failure flow:**
  1. The daily run checkpoints cursor `C` after one page.
  2. An existing user with UUID `< C` registers their first active token without changing timezone.
  3. The user becomes eligible, but subsequent `id > C` pages cannot see them.
  4. Registration does not call direct reschedule because timezone is unchanged.
  5. The job reaches the final page and is marked complete with that user omitted for the day.
- **Minimal correction:** Define snapshot semantics explicitly. Practical minimum: direct-reschedule whenever a user gains their first active token, freeze a run upper bound/watermark, and document that mutations behind the cursor are handled by write-side reschedule. Add the composite batching index required by the final query shape and an integration test for eligibility gained behind the cursor.

## Cross-Cutting Review Checklist

- **Concurrency:** Failed — notification fencing, lease-loss overlap, cleanup/claim race, and supervision crash loop need correction.
- **Error boundaries:** Failed — provider calls lack a bounded deadline compatible with lease/shutdown guarantees.
- **API/contracts:** Failed — per-workload control flags and retry/fencing contracts are assumed by rollout but not defined by the runtime phase.
- **Backwards compatibility:** Failed — notification schema/claim migration and mixed cron/worker claimant behavior are absent.
- **Input validation:** No new external input surface in scope; cursor/limit validation is stated.
- **Auth/authz:** Protected health/no public run-now control is correctly required.
- **Query efficiency:** Gap — final keyset query needs an index matching its actual predicate/order; stale-claim indexes must move from schedule time to claim expiry.
- **Data leaks:** No new leak found; sanitized error/cursor guidance is adequate.
- **Plan fact-check:** File paths, symbols, current phase ordering, transaction boundaries, and behavioral claims above were grep/read-verified against live code.

## Required Plan Corrections, Ordered

1. Fix push-stage executor coverage and define per-workload/sub-phase flags and rollback matrix.
2. Add notification owner/claim-expiry schema and live-claim-safe cleanup semantics.
3. Change worker supervision so auxiliary failure cannot indefinitely crash-loop the primary web service.
4. Add continuous lease heartbeat/provider deadlines and a concrete fairness algorithm.
5. Make resource guards container-scoped and cursor semantics mutation-safe.
6. Explicitly preserve the seven-day lifecycle-email suppression contract.

## Unresolved Questions

- None requiring a business decision. All corrections preserve the approved architecture and operating constraints.

**Status:** DONE
**Summary:** Completed hard-mode failure-flow review with 10 evidence-backed findings; four are critical blockers to implementation/cutover.
**Concerns/Blockers:** Plan needs the ordered corrections above before implementation is production-safe.
