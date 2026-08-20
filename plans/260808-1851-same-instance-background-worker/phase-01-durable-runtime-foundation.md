---
phase: 1
title: "Durable Runtime Foundation"
status: pending
priority: P1
effort: "2-3 days"
dependencies: []
---

# Phase 1: Durable Runtime Foundation

## Context Links

- [Overview](./plan.md)
- [Worker coordination research](./research/researcher-01-worker-coordination-and-process-lifecycle.md)
- `src/infra/database/config_async.py`
- `src/infra/database/models/`
- `src/infra/config/settings.py`

## Overview

Create the smallest durable scheduler substrate: one PostgreSQL lease row per worker group plus job-run rows only for cursor-based scheduled scans. Native notification and affiliate queues remain authoritative for continuous drains. This phase supplies coordination only; it does not move a workload yet.

## Key Insights

- Render can overlap old and new containers during deploys, so process-local locks are insufficient.
- A PostgreSQL lease works with the existing stack and avoids a new broker. Acquisition/renewal must be conditional and short-lived.
- Each worker process uses two total DB permits in both pool modes. A one-permit ordinary-workload gate prevents both permits being consumed by workload DB sections, leaving coordination capacity for heartbeat/lease work. Claims are serialized separately; Phase 5 separately budgets aggregate connections during process overlap.
- The worker must own its database engine/session lifecycle and configuration instead of depending on the API process or Uvicorn-oriented pool globals; this is the seam for later separate hosting.
- External calls must never happen while the scheduler transaction or lease row is locked.

## Requirements

- At most one active scheduler owns the lease, while an expired lease is safely reclaimable.
- Every scheduled scan has a deterministic unique key, durable status, retry metadata, optional JSON cursor, and retention timestamp. Queue drains do not get duplicate aggregate run state.
- Claim/complete/fail mutations verify owner token plus a monotonic lease epoch and use database time to reduce clock-skew risk.
- Worker defaults are conservative and independently configurable without changing existing cron behavior.
- Workload concurrency defaults to two, with one active batch per job type; the controller may admit only one or zero batches under pressure.
- Coordination and progress use PostgreSQL only. No localhost IPC, process memory, or container filesystem state may be required for correctness.

## Architecture

`BackgroundWorkerLease` coordinates singleton scheduling and increments a fencing epoch at every takeover. It records an opaque process instance ID, `colocated`/`dedicated` hosting mode, and one bounded sanitized health snapshot for cross-service visibility without exposing host details. `BackgroundJobRun` records only a cursor-based scheduled scan and its progress. `BackgroundJobRepository` exposes atomic acquire, renew, release, health update, create-or-load, claim, checkpoint, complete, fail, and terminal-history prune operations. All operations commit before workload I/O.

## Related Code Files

### Create

- `migrations/versions/20260808000001_add_background_job_runtime.py`
- `src/infra/database/models/background_job.py`
- `src/infra/repositories/background_job_repository.py`
- `tests/unit/infra/repositories/test_background_job_repository.py`
- `tests/integration/postgres/test_background_job_repository.py`

### Modify

- `src/infra/database/models/__init__.py`
- `src/infra/config/settings.py`
- `src/infra/database/connection_policy.py`
- `src/infra/database/config_async.py`
- `src/infra/database/uow_async.py`
- `.env.example`
- `tests/unit/infra/database/test_model_registry_metadata.py`

## Implementation Steps

1. Add the Alembic revision on down-revision `20260807000002`. Create `background_worker_leases` keyed by lease name with owner, opaque per-boot process UUID, hosting mode, expiry, heartbeat, monotonically increasing epoch, health freshness, last success/failure, sanitized failure code, pause/degraded state, cgroup CPU/memory samples, and a size/key-bounded per-workload outcome/lag/count/duration snapshot. Owner/epoch-fence health writes and preserve the last snapshot across release/takeover. Create `background_job_runs` with a unique `(job_name, schedule_key)`, status, owner token, lease epoch, available/lease timestamps, attempts, cursor JSON, timestamps, and bounded error text. Add due-state and terminal-retention indexes; keep downgrade limited to these objects.
2. Add SQLAlchemy models and export them through the model registry so Alembic metadata and application imports agree. Use timezone-aware database timestamps and explicit status values (`pending`, `processing`, `completed`, `failed`).
3. Implement repository methods with conditional ownership updates and affected-row verification. Copy `(owner_token, lease_epoch)` into scan claims; require both plus a still-current lease for checkpoint/complete/fail. Treat ownership loss as a normal outcome.
4. Add exact default-false execution flags: `BACKGROUND_WORKER_ENABLED`, `BACKGROUND_WORKER_SHADOW_MODE`, `BACKGROUND_JOB_AFFILIATE_ENABLED`, `BACKGROUND_JOB_EMAIL_ENABLED`, and `BACKGROUND_JOB_PUSH_ENABLED`. Add `BACKGROUND_WORKER_HOSTING_MODE=colocated` with only `colocated|dedicated`, generate an opaque UUID on every process boot, and add `BACKGROUND_WORKER_MAX_CONCURRENCY=2`, `BACKGROUND_WORKER_DB_CONCURRENCY=2`, and `BACKGROUND_WORKER_WORKLOAD_DB_CONCURRENCY=1`; reject higher values in this instance profile. The push flag gates all four notification steps.
5. Add poll/yield, lease TTL/renewal, provider/step deadline, wall-time budget, retry/backoff, batch, resource guard, `BACKGROUND_WORKER_SECOND_SLOT_MAX_UTILIZATION=70`, and `BACKGROUND_JOB_RUN_RETENTION_DAYS=30`. Preserve ceilings: notification/precompute/trial 100, affiliate 50, cleanup 500, email 25, CPU 85%, normal memory 75%, peak memory 85%. Start slot two only while both CPU and memory are below 70%; pause new work at hard limits.
6. Extract a side-effect-free connection-policy/async-engine/session/UoW builder that accepts explicit settings. Keep current API engine/session globals only as a compatibility wrapper over that builder. The worker builder uses optional `BACKGROUND_WORKER_DATABASE_URL` and `BACKGROUND_WORKER_DB_CONNECTION_MODE`, falling back to the app runtime URL/mode, plus `BACKGROUND_WORKER_DB_POOL_SIZE=2`, `BACKGROUND_WORKER_DB_MAX_OVERFLOW=0`, and worker-specific timeout/recycle settings. Do not mutate environment values, import/initialize the API singleton path, or reuse the API engine. Inject this worker session/UoW factory into every worker workload and route every DB opening through its gate. In `NullPool` mode, the total-session semaphore—not pool size—enforces the two-connection cap.
7. Define the worker DB contract: total session gate 2, ordinary-workload DB gate 1, and a coordination/claim lock. Required order is workload gate (if applicable) -> coordination lock (claims only) -> total session permit; never acquire/upgrade a coordination lock while holding a DB session. Heartbeat acquires coordination lock -> total permit, has priority when renewal is due, and uses acquisition/statement deadlines below the renewal safety margin.
8. Prune only terminal scan runs older than retention in bounded chunks; never prune active/failed-retry state or native queue rows.
9. Unit-test state transitions/config validation, API/worker engine isolation, exactly one standalone worker engine, injected UoW use, engine closure on every exit, bounded durable health/freshness, and run PostgreSQL tests for simultaneous acquisition across both hosting modes, epoch takeover, stale-owner rejection, deterministic scan creation, checkpoint resume, bounded retention, both DB modes, and explicit migration `20260807000002 -> new revision -> 20260807000002 -> head`.

## Todo List

- [ ] Add runtime-state migration and models.
- [ ] Implement atomic lease and run repository.
- [ ] Add conservative worker configuration and validation.
- [ ] Isolate worker DB engine/session lifecycle from the API runtime.
- [ ] Persist a bounded owner-fenced worker health snapshot.
- [ ] Add three cron-granularity flags, two-slot admission, and terminal retention.
- [ ] Prove concurrency semantics against PostgreSQL.
- [ ] Verify migration round-trip from current head.

## Success Criteria

- [ ] Two contenders cannot both hold an unexpired lease.
- [ ] A crashed owner becomes reclaimable after TTL and its old epoch cannot mutate the new owner's run.
- [ ] Recreating a schedule key returns the same logical run instead of duplicating it.
- [ ] Cursor and retry state survive process restart.
- [ ] Worker sessions never exceed two; ordinary workload DB sections never exceed one; heartbeat meets renewal deadline under saturated direct-pool and Neon-pooler modes.
- [ ] Colocated and dedicated-mode contenders coordinate through the same durable lease without local IPC or filesystem state.
- [ ] Protected health remains meaningful before, during, and after lease takeover, including freshness and last queue-drain outcomes.

## Risk Assessment

- **Lease expires during slow I/O:** Phase 4 adds an independent heartbeat, bounded provider deadlines, and fencing; external exactly-once still depends on provider/native-row idempotency.
- **Database outage:** web traffic remains independent; worker backs off with jitter and does not spin.
- **State table growth:** retain compact summaries and bounded-prune terminal scan runs after 30 days; do not store payload bodies.

## Security Considerations

Owner tokens are random per process, errors are sanitized, and cursor JSON contains identifiers only—not tokens, email bodies, or provider responses. Repository access remains internal and uses existing database credentials.

## Next Steps

Phase 2 uses this substrate to make notification work bounded and resumable. Phase 3 can proceed after this phase in parallel with Phase 2.
