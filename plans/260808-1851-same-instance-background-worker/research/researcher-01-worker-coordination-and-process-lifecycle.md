# Research Report: Same-Instance Background Worker Process

## Executive Summary
Best fit is a **sibling worker inside the same Render web service container**, but **not** a raw in-memory cron loop. Use a small DB-backed coordinator: a durable job table plus a single leader lease, then execute due work in short-lived async transactions. This matches the current async SQLAlchemy runtime, survives Render rolling deploy overlap, and keeps recovery visible in Postgres instead of hidden in process memory.

The coordination primitive should be **a lease row first, advisory lock second**. Lease gives durability, explicit ownership, and crash recovery after SIGTERM or instance loss. Advisory lock is still useful as a narrow guard around "claim next batch" to prevent double-claim races, but it should not be the only source of truth because it has no explicit state or TTL. The worker should renew heartbeats frequently, stop on SIGTERM, and rely on Render's shutdown window to finish or requeue work.

## Research Methodology
- Sources consulted: 7 primary sources
- Date range of materials: current docs as crawled on 2026-08-08 plus current repo state
- Key search terms used: Render deploy overlap, Render SIGTERM shutdown, PostgreSQL advisory locks, SQLAlchemy async transaction, Python signal handlers, async session lifecycle, background task manager

## Key Findings

### 1. Current Repo Shape
- The app already has a managed background-task lifecycle in `src/api/main.py`: startup creates a process-wide task manager, and shutdown drains it before cache/engine teardown. See [src/api/main.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/main.py#L176-L276).
- `BackgroundTaskManager` tracks spawned tasks and explicitly cancels them so DB connections can be released before engine disposal. See [src/infra/event_bus/background_task_manager.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/event_bus/background_task_manager.py#L11-L50).
- The runtime is async-first. `AsyncUnitOfWork` uses a single async session per scope and guards concurrent reuse with `asyncio.Lock`; DB state is expected to be short-lived and request/job scoped. See [src/infra/database/uow_async.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/uow_async.py#L89-L165) and [docs/database-guide.md](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/database-guide.md#L79-L81).
- Render service startup is currently `uvicorn src.api.main:app --workers ${UVICORN_WORKERS:-4}` from `docker-entrypoint.sh`, so the process model is already multi-worker unless overridden. See [docker-entrypoint.sh](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docker-entrypoint.sh#L34-L42) and [src/infra/config/settings.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py#L75-L75).
- The repo already uses standalone cron entrypoints for push/email/affiliate work, but those are fire-and-exit processes, not a durable sibling worker. See [src/cron/push.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/cron/push.py#L1-L5), [src/cron/email.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/cron/email.py#L1-L5), and [src/cron/affiliate_outbox.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/cron/affiliate_outbox.py#L1-L5).

### 2. Render Runtime Reality
- Render says only one deploy runs at a time per service, but overlapping deploys still happen; the platform can wait for the in-progress deploy or cancel it based on workspace policy. Source: https://render.com/docs/deploys
- Render periodically swaps instances during deploys and maintenance. It sends `SIGTERM` and gives a 30-second graceful shutdown window, extendable to 300 seconds. Source: https://render.com/docs/websocket
- That means a "single instance" assumption is false during rollout. Old and new instances can overlap long enough for duplicate schedulers unless coordination is explicit.

### 3. Python + SQLAlchemy Behavior
- Python signal handlers run in the main thread of the main interpreter only. A worker should keep its SIGTERM handling simple and process-wide, not thread-local. Source: https://docs.python.org/3/library/signal.html
- SQLAlchemy async transactions support explicit `commit()`, `rollback()`, and `close()` semantics; `close()` rolls back the base transaction if one is active. Source: https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html
- The repo already codifies the same idea: async DB units should be scoped, short-lived, and not shared concurrently. See [docs/database-guide.md](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/database-guide.md#L224-L226) and [docs/system-architecture.md](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/system-architecture.md#L222-L223).

### 4. PostgreSQL Coordination Options
- PostgreSQL advisory locks are legitimate application-controlled locks. Source: https://www.postgresql.org/docs/current/explicit-locking.html
- `pg_try_advisory_lock` / `pg_try_advisory_xact_lock` are non-blocking and return immediately if the lock cannot be acquired. Source: https://www.postgresql.org/docs/current/functions-admin.html
- Advisory locks are a good mutual-exclusion primitive, but they are not a durable ownership record. They disappear with the session and give you no native TTL/heartbeat metadata.
- A lease row gives the opposite trade-off: durable ownership state, visible heartbeat, TTL-based failover, and easy introspection. It costs one extra table and one renewal loop.

## Comparative Analysis

| Option | Performance | Complexity | Maintenance | Crash recovery | Fit here |
|---|---:|---:|---:|---:|---:|
| In-memory scheduler only | Best | Lowest | Low at first, then high | Poor | Bad |
| PostgreSQL advisory lock only | Good | Low | Low | Good for dead session, weak for observability | Medium |
| Lease row only | Good | Medium | Medium | Strong | Best |
| Lease row + advisory lock | Good | Medium-high | Medium | Strongest | Best if worker claims can race |

### Ranking
1. **Lease row as primary leader election**
1. **Lease row + advisory lock around claim/update critical section**
1. Advisory lock only
1. In-memory scheduler only

### Why lease wins
- Handles SIGTERM/instance swaps cleanly by letting the old owner stop heartbeating and the new owner acquire after TTL.
- Gives a durable audit trail: `owner_id`, `lease_expires_at`, `heartbeat_at`, `last_success_at`, `last_error_at`.
- Makes health/debugging trivial from SQL.

### Why advisory lock still matters
- It is useful for a very small critical section, for example "pick next eligible job batch and mark it claimed."
- It reduces double-claim risk when two contenders wake at the same time.
- It should not be the sole leadership model because the lock itself does not describe "who owns the worker" or "when do we fail over."

## Implementation Recommendation

### Recommended Design
Use a sibling worker entrypoint in the same container, but keep the coordination in Postgres:

```text
Render web service process
├─ FastAPI app / Uvicorn workers
└─ Background worker loop
   ├─ acquire/renew lease row
   ├─ claim due jobs in short transactions
   ├─ execute job
   ├─ write outcome + next run state
   └─ heartbeat until SIGTERM
```

### Durable Job Schema
Minimum tables:
- `worker_leases`
- `scheduled_jobs`
- `job_executions` or `job_attempts`

Minimal fields:
- `worker_leases`: `lease_name`, `owner_id`, `lease_expires_at`, `heartbeat_at`, `started_at`
- `scheduled_jobs`: `job_type`, `payload`, `run_at`, `status`, `locked_by`, `locked_at`, `attempt_count`, `last_error`, `dedupe_key`
- `job_attempts`: `job_id`, `attempt_no`, `started_at`, `finished_at`, `status`, `error`

### Lifecycle
1. On startup, worker generates an owner id and tries to acquire the lease.
2. If lease acquisition fails, the process stays passive and keeps retrying.
3. If lease acquisition succeeds, worker heartbeats on a short interval.
4. Each loop uses a fresh async session, claims a small batch, commits, then processes outside the claim transaction.
5. On SIGTERM, stop accepting new work, finish or requeue the active job, stop heartbeating, and exit before Render's shutdown window closes.

### Observability
Keep this minimal:
- one health endpoint for app readiness
- one worker-state metric/gauge or structured log line for `leader|follower|stopping`
- one heartbeat timestamp in DB
- one error counter for failed claims/executions

## Security Considerations
- Do not put secrets, payload bodies, or raw user data in the lease row.
- Keep worker identity opaque and non-guessable.
- Use idempotency keys on scheduled jobs so duplicate claims after crash/retry do not duplicate side effects.

## Performance Insights
- A lease row plus claim query is cheap enough for this stack.
- The bigger performance risk is not the leader check; it is holding a DB session open across external I/O.
- Therefore: claim, commit, close session, then do work. Reopen session only for state changes.

## Architectural Fit
- Strong fit with current FastAPI + async SQLAlchemy + Postgres stack.
- Strong fit with Render's graceful shutdown model.
- No new broker, no paid separate worker, no Celery.
- Matches current repo direction: async runtime, explicit task lifecycle, observable boundaries, and Postgres as source of truth.

## Limitations
- I did not inspect a live Render service config from this repo because none was present in the checked files.
- I did not benchmark the lease-query path under production traffic.
- I did not inspect every existing cron job's exact side effects; the recommendation assumes they can be converted to idempotent job handlers.

## Official References
- Render deploy overlap: https://render.com/docs/deploys
- Render SIGTERM/shutdown: https://render.com/docs/websocket
- Python signal handling: https://docs.python.org/3/library/signal.html
- PostgreSQL explicit locking: https://www.postgresql.org/docs/current/explicit-locking.html
- PostgreSQL advisory lock functions: https://www.postgresql.org/docs/current/functions-admin.html
- SQLAlchemy asyncio transactions: https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html

## Next Step
Implement the lease table and worker loop behind a small entrypoint, then migrate push/email/affiliate cron logic into idempotent scheduled jobs.

## Unresolved Questions
- Should the worker own all three cron domains immediately, or should push/email/affiliate be migrated one at a time?
- What retry/backoff policy should govern lease acquisition during deploy overlap?
- Do we want one shared scheduler table for all domains, or separate tables per domain for simpler ops?
