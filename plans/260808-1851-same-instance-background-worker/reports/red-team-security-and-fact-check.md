# Red-Team Security and Fact Check

## Scope

- Reviewed every file in `plans/260808-1851-same-instance-background-worker/`: `plan.md`, phases 01-05, and both research reports.
- Cross-checked the live health/auth routes, notification queue/model, Firebase path, lifecycle email port/adapter/service, affiliate outbox, database connection policy, cron entrypoints, Docker entrypoint, and current Alembic head.
- Preserved approved decisions: same Render instance, one sibling worker, no new broker, all cron workloads, and approved thresholds/batches.
- Review type: hostile static plan review. No application code changed and no tests run.

## Overall Assessment

**BLOCKED pending plan correction.** The deployment shape is viable, and the Resend SDK claim is factually correct, but the plan currently carries one direct privacy leak forward, lacks complete lease fencing, cannot implement notification owner checks with the listed schema/files, and defines a rollout that stops part of the existing push workload. Several acceptance criteria also contradict the specified process and shadow behavior.

## Findings

### 1. Critical — Dispatch continues to trust stale FCM token snapshots

- **Plan location:** `phase-02-bound-notification-workloads.md:35-36,94-96` promises existing idempotency and privacy filters remain intact; `phase-02-bound-notification-workloads.md:63-66` changes batching/claims but does not require recipient revalidation at dispatch.
- **Repository evidence:** `src/infra/database/models/notification/notification.py:27-29` explicitly says recipient truth must come from normalized `user_fcm_tokens`, not context JSON. However `src/infra/services/daily_context_precompute_service.py:674-679` writes FCM tokens into the notification context, and `src/infra/services/cron_notification_dispatch_service.py:105-107` sends those stored tokens without re-reading active tokens. Token deactivation occurs only after a provider failure (`src/infra/services/cron_notification_dispatch_service.py:209-210,318-339`).
- **Failure/exploit scenario:** a user logs out, removes a device, or has a token deactivated after precompute but before delivery. The background worker still sends nutrition/reminder content to the old device because the queue snapshot remains authoritative in practice. This can expose private health-related content after authorization/recipient state changed.
- **Minimal plan correction:** require dispatch-time hydration from `user_fcm_tokens WHERE is_active = true` for the claimed user IDs; do not send `context.fcm_tokens`. Add a test that deactivates/replaces a token after precompute and before dispatch and proves the stale token receives no call.

### 2. Critical — Lease renewal and fencing do not cover in-flight provider I/O

- **Plan location:** `phase-01-durable-runtime-foundation.md:60-64,78,85` uses random owner tokens and renews between batches; `phase-04-sibling-worker-and-process-supervision.md:63-66` likewise renews between steps and explicitly does not stop an in-flight provider call.
- **Repository evidence:** the current FCM boundary is a synchronous, potentially long-running provider call with no local deadline argument (`src/infra/services/firebase_service.py:164-173`); affiliate I/O alone allows a 10-second configured timeout (`src/infra/adapters/affiliate_service_adapter.py:104-108`, `src/infra/config/settings.py:319-322`). The plan moves FCM to a thread, which prevents event-loop blocking but does not stop the thread when the lease expires.
- **Failure/exploit scenario:** owner A starts an external send; the call stalls beyond the lease TTL. Because renewal occurs only between steps, owner B acquires the expired lease and starts the same logical work. A's provider call can still complete. Random owner equality on a run row is not a fencing generation and cannot prevent the already-issued side effect; if B has not replaced A's run claim yet, A may also persist completion after losing scheduler leadership.
- **Minimal plan correction:** add an independent heartbeat task that runs during external I/O; add a monotonic lease epoch/fencing token incremented on every acquisition and copied into each claim. Completion/checkpoint/fail must require `(owner_token, lease_epoch)` and a still-current unexpired lease. Bound provider-call deadlines below TTL (or define explicit ambiguity handling), and test a paused old owner attempting send completion after takeover.

### 3. High — Notification owner-conditional completion is impossible with the current schema and listed changes

- **Plan location:** `phase-02-bound-notification-workloads.md:65,69,84-85` requires a claim owner token and rejects stale owners. Its related files at `phase-02-bound-notification-workloads.md:46-53` list no notification model or migration and name a repository that does not exist.
- **Repository evidence:** `src/infra/database/models/notification/notification.py:32-45` has only `status`; it has no claim token, lease epoch, or claim timestamp. Current completion predicates only check `status = 'processing'` and IDs (`src/infra/services/cron_notification_dispatch_service.py:250-285`). Stale recovery can reset every old processing row without an owner predicate (`src/infra/services/cron_notification_dispatch_service.py:294-310`).
- **Failure/exploit scenario:** A claims a row and stalls. Recovery resets it; B claims and sends it. A resumes and its `WHERE status='processing' AND id IN (...)` update can mark B's claim sent/retry/failed. The same missing fence permits concurrent duplicate sends during cron/worker overlap.
- **Minimal plan correction:** explicitly add notification schema/model changes for `claim_token`, `claim_epoch`, and `claimed_at`/`claim_expires_at`; include them in claim, recovery, and every result mutation predicate. Add an affected-row assertion and a PostgreSQL test where A resumes after B reclaims.

### 4. High — Staged cutover disables trial/cleanup before their worker stages are enabled

- **Plan location:** `phase-05-verification-and-staged-cron-cutover.md:63` enables dispatch/precompute and then disables the push cron; `phase-05-verification-and-staged-cron-cutover.md:65` enables trial reminders later. The research repeats this order at `research/researcher-02-batching-delivery-and-rollout.md:207-218`.
- **Repository evidence:** the single push cron runs precompute, trial scheduling, dispatch, and cleanup in one invocation (`src/cron/push.py:67-85,94-103,111-131`). There is no separate Render-compatible trial or cleanup entrypoint.
- **Failure/exploit scenario:** after stage 1 disables the push cron, trial reminders and cleanup stop until later stages. A subscription entering the reminder window in that gap may never get its row. Rollback "per workload" has the inverse problem: re-enabling the push cron also restarts all four phases, including phases still owned by the worker.
- **Minimal plan correction:** cut over the four push subworkloads as one atomic group, or first add explicit per-phase compatibility flags/entrypoints. Do not disable the push cron until precompute, trial, dispatch, and cleanup are all enabled and observable in the worker. Update rollback drills to operate on the same granularity.

### 5. High — Worker crash handling contradicts the web-availability success gate

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:28,41,67,83` terminates the surviving child and exits non-zero when either child exits. `phase-05-verification-and-staged-cron-cutover.md:84` requires the web service to remain available through a worker crash.
- **Repository evidence:** this is a single web service container whose current PID 1 directly execs Uvicorn (`docker-entrypoint.sh:34-42`). Under the proposed two-child rule, killing Uvicorn after worker death necessarily drops the only instance until Render restarts it.
- **Failure/exploit scenario:** a deterministic worker startup/configuration bug crash-loops the entire web service, turning a background-work defect into customer-facing API downtime. The enabled worker becomes part of web liveness despite the plan saying web is primary.
- **Minimal plan correction:** supervise/restart the worker locally with bounded exponential backoff while Uvicorn stays alive; expose degraded worker health and fail the container only after an explicit retry/time budget. Otherwise remove the web-availability claim and treat worker death as accepted web restart downtime.

### 6. High — Bounded cleanup can delete rows while another executor is sending them

- **Plan location:** `phase-02-bound-notification-workloads.md:34,67-69,84-85` says cleanup becomes bounded and overlap-safe but does not constrain eligible statuses or ownership. `phase-05-verification-and-staged-cron-cutover.md:40` relies on brief cron/worker overlap being safe.
- **Repository evidence:** current cleanup deletes every expired row regardless of status (`src/infra/services/cron_notification_dispatch_service.py:287-292`). Provider I/O occurs after the claim transaction and before result marking (`src/infra/services/cron_notification_dispatch_service.py:181-218`).
- **Failure/exploit scenario:** during cron/worker overlap or a delayed backlog, one executor sends a `processing` row while cleanup deletes it. The provider accepts the notification, but result persistence updates zero rows. State/history is lost, and retry/duplicate behavior becomes unknowable.
- **Minimal plan correction:** define cleanup eligibility explicitly: never delete active `processing` claims; delete only terminal rows or expired unclaimed rows with an owner-safe predicate. Add a concurrent cleanup-vs-send PostgreSQL test and assert affected-row counts.

### 7. High — Worker health placement remains ambiguous across public and protected routes

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:56,68,94-96` says to extend the existing protected health route but names only the mixed `health.py` module; `phase-05-verification-and-staged-cron-cutover.md:34,60` asks for health visibility without naming the authenticated endpoint.
- **Repository evidence:** `/health` and `/v1/health` are intentionally unauthenticated (`src/api/routes/v1/health.py:45-59`), and tests assert that public behavior (`tests/unit/api/test_health_router.py:7-35`). Detailed endpoints use `Depends(require_monitoring_access)` (`src/api/routes/v1/health.py:80-81,125-126,180-181`), whose token check fails closed (`src/api/dependencies/auth.py:368-381`).
- **Failure/exploit scenario:** an implementer appends lease owner, heartbeat, lag, failures, or resource pressure to `health_check()` to satisfy "health visibility," exposing deployment timing and worker failure state to unauthenticated callers. That data is useful for outage timing and targeted load attacks.
- **Minimal plan correction:** name a dedicated endpoint, e.g. `GET /v1/health/background-worker`, and require `Depends(require_monitoring_access)`. Keep `/health` and `/v1/health` limited to coarse liveness. Add explicit 403/no-token and response-redaction tests.

### 8. Medium — Shadow-mode acceptance criteria contradict required lease mutations

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:34,64,85` calls shadow mode read-only and says tests must prove no claim/update/delete. `phase-05-verification-and-staged-cron-cutover.md:62` simultaneously requires lease metrics to populate in shadow mode.
- **Repository evidence:** there is no current worker implementation; the plan's own durable design requires lease acquisition/renewal mutations (`phase-01-durable-runtime-foundation.md:33-40,62`). A populated durable lease/heartbeat cannot be produced with zero updates.
- **Failure/exploit scenario:** either the test forbids lease writes and shadow mode cannot exercise leadership/health, or the implementation writes the lease and fails its stated purity gate. Teams may weaken the test broadly, accidentally permitting business mutations too.
- **Minimal plan correction:** define shadow purity as "coordination tables and metrics may mutate; business/queue/provider state may not." Assert an allowlist of lease/heartbeat writes and deny writes to notifications, email/affiliate claims, cursors, and providers.

### 9. Medium — The one-connection guarantee is false in supported `neon_pooler` mode

- **Plan location:** `phase-01-durable-runtime-foundation.md:28,64,81` claims worker settings force a one-connection pool and configuration cannot allocate more than one DB connection.
- **Repository evidence:** `src/infra/database/connection_policy.py:115-124` selects `NullPool` for `neon_pooler` and ignores `ASYNC_POOL_SIZE_PER_WORKER`/`ASYNC_POOL_MAX_OVERFLOW`; `DatabaseConnectionPolicy.total_capacity` reports `0` rather than enforcing a cap (`src/infra/database/connection_policy.py:28-33`). Both direct and Neon pooler modes are supported (`docs/database-guide.md:29-56`).
- **Failure/exploit scenario:** an environment switch to the supported pooler mode silently removes the claimed client-side cap. Concurrent heartbeat, health, and workload sessions can open more than one database connection despite passing the planned environment validation.
- **Minimal plan correction:** either fail worker startup unless `DB_CONNECTION_MODE=direct_pool`, or replace the promise with an explicit concurrency semaphore/session budget that also applies under `NullPool`. Test both supported connection modes.

### 10. Medium — Phase 2 and Phase 3 target non-existent symbols/files and miss the live mutation sites

- **Plan location:** `phase-02-bound-notification-workloads.md:16-18,46-53` names three services under `src/domain`, `notification_repository.py`, `user_repository.py`, and `firebase_notification_adapter.py`; `phase-03-harden-email-and-affiliate-delivery.md:49,63` names `src/domain/ports/email_port.py` and `EmailPort.send_email`.
- **Repository evidence:** push imports the live implementations from `src/infra/services/cron_notification_dispatch_service.py`, `src/infra/services/cron_trial_push_service.py`, `src/infra/services/daily_context_precompute_service.py`, and `src/infra/services/firebase_service.py` (`src/cron/push.py:29-38`). The actual email contract is `EmailServicePort.send_email` in `src/domain/ports/email_service_port.py:16-27`. Trial's unbounded source query is in `src/infra/repositories/subscription_repository_async.py:91-110`.
- **Failure/exploit scenario:** implementation follows the plan inventory, creates parallel abstractions, or changes wrappers while leaving the live unbounded queries and synchronous provider path untouched. Review/tests then target files that production does not execute.
- **Minimal plan correction:** replace every stale path/symbol with the live file/symbol inventory and explicitly include `subscription_repository_async.py`, the notification model/migration, and `email_service.py` as required modification sites.

## Verified Claims / Positive Observations

- Current Alembic head is `20260807000002`; the plan's down-revision statement is current.
- The installed Resend version is pinned to `2.30.1` (`requirements.txt:62`), and its live SDK signature accepts `Emails.send(params, options)` with `options.idempotency_key`. The plan is correct to pass the stable key as the second options object, not inside email params.
- Affiliate network calls are already HMAC-SHA256 signed (`src/infra/adapters/affiliate_service_adapter.py:21-24,93-102`), and the outbox carries a unique provider event ID (`src/infra/database/models/affiliate_event_outbox.py:21-24`).
- Existing detailed monitoring authorization is constant-time and fail-closed (`src/api/dependencies/auth.py:368-381`); reusing it is appropriate.
- Existing affiliate and notification provider I/O already occurs outside claim transactions (`src/infra/services/affiliate_outbox_dispatch_service.py:32-50`; `src/infra/services/cron_notification_dispatch_service.py:234-248,181-218`).

## Behavioral Checklist

- [x] Concurrency: lease expiry/takeover, stale owners, notification recovery, cleanup overlap, process exit order checked.
- [x] Error boundaries: provider exceptions, per-job containment, supervisor crash propagation checked.
- [x] API contracts: health auth, Resend options signature, null/missing live files checked.
- [x] Backwards compatibility: push-cron granularity, email port callers, DB modes, schema additions checked.
- [x] Input validation: cursor/limit caps and health service-token boundary checked; no public job-control endpoint proposed.
- [x] Auth/authz: public vs protected health and dispatch-time recipient authorization checked.
- [x] N+1/query efficiency: current whole-set precompute/trial source queries and bounded-query target files checked.
- [x] Data leaks: FCM recipient snapshots, health detail, logs/error-storage requirements checked.
- [x] Fact-checked: all plan paths/symbols and behavioral claims above grep/read-verified against live repository state.

## Recommended Blocking Corrections

1. Fix dispatch-time token authorization and notification claim fencing/schema.
2. Specify continuous lease renewal plus monotonic fencing through provider ambiguity.
3. Make push cutover/rollback atomic at the actual cron-entrypoint granularity.
4. Reconcile worker-crash behavior with the web availability gate.
5. Name the protected worker-health endpoint and correct shadow-mode mutation semantics.
6. Correct live file/symbol inventory and validate the one-connection promise in both DB modes.

## Unresolved Questions

- None requiring a product decision. All corrections above preserve the approved topology, workload scope, thresholds, and batches.

**Status:** DONE_WITH_CONCERNS
**Summary:** Completed hostile security/fact review with 10 evidence-backed findings; plan is blocked on privacy, lease fencing, ownership schema, rollout granularity, and contradictory acceptance criteria.
**Concerns/Blockers:** Critical stale-recipient delivery and incomplete lease fencing must be corrected before implementation.
