# Hard-Mode Plan Validation

## Result

**PASS for implementation planning after amendments and focused revalidation.** The original 44-claim review remains valid except for serial execution and rollout order, which the user explicitly replaced. Bounded-concurrency and portability contracts were rechecked for cross-file consistency; shared-instance capacity remains runtime-gated in Phase 5.

## Amendment Revalidation

1. User-confirmed current state: notification is running; lifecycle email and affiliate are dormant.
2. Every plan file caps workload concurrency at two and forbids same-job double batches.
3. Dispatch is the urgent lane; precompute, trial, and cleanup share one mutually exclusive maintenance lane.
4. Worker DB/session concurrency is two in both pool modes; ordinary workload DB access is one, reserving coordination capacity, with one lock/permit acquisition order.
5. The independent heartbeat does not consume a workload slot.
6. Phase 5 enables only the push flag and removes only the active push cron.
7. Dormant flags produce no claims, provider calls, workload slots, or initial capacity evidence.
8. Existing batch ceilings and CPU/memory/p95 thresholds are unchanged.
9. Slot-two admission is explicit at below 70% CPU/memory; effective concurrency reduces to one or zero without redesign while hard gates remain unchanged.

The focused amendment reviewer initially blocked on heartbeat starvation. The final plan resolves it with two total permits, one ordinary-workload permit, due-time coordination priority, a single acquisition order, bounded DB waits/statements, and a combined contention test in both pool modes.

## Portability Amendment Revalidation

1. The initial deployment remains colocated on the existing Standard web service.
2. `python -m src.background_worker` is the single standalone worker command in either topology.
3. Worker DB/provider/session/shutdown lifecycle is independent of FastAPI, Uvicorn, and the web entrypoint.
4. `docker-entrypoint.sh` is only the colocated supervisor adapter; the same image runs the command directly in dedicated mode.
5. PostgreSQL is the only coordination, progress, fencing, and detailed-health source; no localhost IPC or local persistent state is permitted.
6. Worker-specific DB URL/mode/pool settings avoid coupling future service sizing to API engine globals while preserving safe fallbacks.
7. Durable health records hosting mode plus opaque instance identity and remains readable from the protected API route across services.
8. Tests cover same-image startup, standalone SIGTERM/exit behavior, cross-mode lease overlap/takeover, and a schema-free topology handoff.
9. Separate service provisioning and cutover remain excluded from the current implementation scope.
10. The existing HTTP-only Docker health check is explicitly replaced with hosting-mode-aware web and standalone probes, avoiding a hidden local-port dependency.
11. Worker database construction is side-effect-free and explicit-settings based; every worker workload receives the worker session/UoW factory instead of binding to API globals.
12. The lease group persists a bounded, owner/epoch-fenced health snapshot with explicit freshness across takeover.
13. Render environment changes are restart/deploy operations; rollback and handoff drain old workers through SIGTERM before enabling the replacement executor.
14. Two database permits are per worker process. Direct API overlap uses configured pool capacity; `NullPool` never contributes zero and instead uses 150% of a representative measured client-connection peak with a floor of 10 per overlapping instance. Both modes add worker permits and a 20%/10-connection reserve, fail closed on missing evidence, and are tested against the relevant provider limit.
15. CPU percentage is defined from cgroup usage deltas normalized by quota/period over monotonic time, with invalid states failing closed.

## Verification Roles

| Role | Checks | Result |
|---|---|---|
| Repository detective | Current cron inventory, live service/model/port paths, config names, migration head, docs/tests | Verified |
| Architecture verifier | App/domain/infra placement and import constraints | `lint-imports`: 4 kept, 0 broken |
| Behavior/test verifier | Claim/retry/cursor/provider flows, CI discovery, failure and rollback tests | Plan covers observed gaps |
| Operations verifier | Render overlap/shutdown assumptions, process lifecycle, resource/latency gates, cutover granularity | Two runtime gates retained |

## Phase Evidence

### Phase 1 — Durable Runtime Foundation

- Verified current Alembic head is `20260807000002` with `alembic heads`.
- Verified live config/runtime files are `src/infra/config/settings.py`, `src/infra/database/config_async.py`, and `src/infra/database/connection_policy.py`.
- Verified direct-pool defaults are worker-count based, while `neon_pooler` uses `NullPool`; the amended plan caps worker sessions at two and serializes claim sections in both modes.
- Verified no existing background lease/run model conflicts with the proposed tables.
- Verified real PostgreSQL CI tests are discovered under `tests/integration/postgres/`.
- Verified the plan limits generic runs to cursor scans and retains native queue authority.
- Verified monotonic epoch, ownership predicates, bounded terminal retention, and complete migration-boundary tests are specified.

### Phase 2 — Bound Notification Workloads

- Verified the push cron contains precompute, trial, dispatch, and cleanup in one entrypoint (`src/cron/push.py`).
- Verified current precompute has an unsafe any-row sentinel and stores FCM token snapshots.
- Verified current precompute batch data still calls per-user weekly-budget logic, so query-count work is required.
- Verified notification claim has no limit/owner fields and reclaim uses scheduled time rather than claim time.
- Verified dispatch uses stored tokens and loses row/token identity when grouping provider calls.
- Verified cleanup deletes expired rows regardless of live processing state.
- Verified the plan now includes schema fencing, dispatch-time active-token hydration, per-row outcomes, snapshot mutation handling, query budget, and cleanup race tests.

### Phase 3 — Email and Affiliate Delivery

- Verified live port is `EmailServicePort.send_email`; lifecycle calls pass through two `EmailService` methods before the adapter.
- Verified Resend 2.30.1 supports `Emails.send(params, options)` and `options.idempotency_key`.
- Verified `EMAIL_ENABLED=false` currently returns success and would be unsafe for durable claim completion.
- Verified current lifecycle queries are unbounded, unordered, and use per-recipient seven-day suppression queries.
- Verified affiliate claiming leaves status pending and has no owner/expiry; a migration is mandatory.
- Verified downstream affiliate `event_id` is unique and suitable for provider dedupe.
- Verified the plan now defines daily scan cursors, exact key propagation, disabled/deferred semantics, suppression preservation, native outbox authority, and concurrent claimant tests.

### Phase 4 — Worker and Supervision

- Verified current entrypoint `exec`s Uvicorn and needs explicit sibling supervision.
- Verified the approved brainstorm calls for supervisor restart with backoff; the plan restarts only the auxiliary worker while Uvicorn remains primary.
- Verified current architecture forbids app-to-infra and infra-to-app imports; orchestration is now assigned to application layer with injected protocol implementations.
- Verified public health endpoints are unauthenticated while detailed routes use `require_monitoring_access`; the worker endpoint is explicitly protected.
- Verified process-only RSS/CPU cannot enforce shared-container limits; cgroup measurement and unavailable-metric fail-closed behavior are specified.
- Verified every workload now has cadence, state authority, lane, initial state, catch-up, and completion semantics.
- Verified two-slot admission, per-job exclusion, independent heartbeat/fencing, shadow mutation allowlist, and worker restart tests are specified.

### Phase 5 — Verification and Cutover

- Verified repository test policy uses scoped unit tests and a dedicated PostgreSQL CI job; plan commands match it.
- Verified there is no `render.yaml`; Render flags and cron deletion require an operator runbook/dashboard action.
- Recorded the direct user amendment: notification is the only initial rollout; email and affiliate remain disabled.
- Verified the push cron must move as one bundle; rollout and rollback now use three exact cron-granularity flags.
- Verified schema-free operational rollback preserves durable state.
- Verified all new migration boundaries, Docker lifecycle, DB modes, cgroup behavior, import contracts, provider ambiguity, and concurrency races have named checks.
- Verified archived roadmap/changelog files are not treated as live documentation authority.

## Runtime-Gated Claims

1. **[UNVERIFIED until staging]** Two concurrent notification batches remain below CPU, memory, DB-connection, and web-p95 gates. Admission must reduce to one or zero if not.
2. **[UNVERIFIED until staging]** Render exposes usable cgroup v2 container counters in this service runtime. Active mode fails closed for new claims if it does not.
3. **[UNVERIFIED until runbook setup]** The live telemetry stack can produce the approved API p95 baseline/comparison before cron disablement.

These are phase gates, not open design questions. CPU, memory, latency, lag, and midnight behavior cannot be honestly proven by static review.

## Commands Run

```text
alembic heads       -> 20260807000002 (head)
lint-imports        -> 4 contracts kept, 0 broken
ck plan status ...  -> 5 pending phases, valid metadata/links
git diff --check    -> clean for plan artifacts
rg whitespace/merge-marker checks -> clean for new untracked plan, report, brainstorm, and journal artifacts
```

## Questions Asked

0. The user directly supplied the amended concurrency and current-workload decisions; validation found no remaining product ambiguity.

## Final Consistency Status

- Plan phase dependencies are acyclic: 1 -> (2,3) -> 4 -> 5.
- Concurrency two, one-batch-per-job, notification-first rollout, dormant flags, batch ceilings, and thresholds are consistent across files.
- The standalone worker, explicit DB/session injection, durable health snapshot, restart-based handoff, mode-specific connection budget, and normalized cgroup sampling are consistent across files.
- No stale path/symbol or superseded first-cutover wording remains after the final sweep.
- Implementation status remains pending; no application code or deployment state was changed.
