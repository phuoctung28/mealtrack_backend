---
phase: 4
title: "Portable Worker and Colocated Supervision"
status: pending
priority: P1
effort: "1-2 days"
dependencies: [2, 3]
---

# Phase 4: Portable Worker and Colocated Supervision

## Context Links

- [Overview](./plan.md)
- [Process lifecycle research](./research/researcher-01-worker-coordination-and-process-lifecycle.md)
- `docker-entrypoint.sh`
- `Dockerfile`
- `src/api/routes/v1/health.py`
- `src/infra/monitoring/observability.py`

## Overview

Build the scheduler as a standalone process, then supervise that same executable beside Uvicorn in the existing container. The web server remains primary in colocated mode; the worker owns its lifecycle, runs at most two different job batches, caps DB sessions at two, and dynamically reduces admission under resource pressure. The same image and command can later run as a separately hosted worker.

## Key Insights

- The current entrypoint ends with `exec uvicorn`; sibling mode needs explicit two-child signal forwarding and exit handling.
- Deployment success must still depend on the web server. A worker crash should be visible and restartable, but must not silently leave an apparently healthy container forever.
- Process RSS is insufficient for the 2 GB instance threshold because API and worker are siblings. Runtime guards must read Linux cgroup container counters; Render metrics remain cutover authority.
- Colocated supervision is a deployment adapter. Worker startup, shutdown, health, database sessions, and scheduling cannot depend on Uvicorn or an API-process import.

## Requirements

- In colocated mode, exactly one Uvicorn worker and one background-worker process run when enabled; existing single-Uvicorn-process startup remains when disabled. Dedicated mode runs only the standalone worker command and never starts Uvicorn.
- `python -m src.background_worker` starts and stops independently in either hosting mode. It uses no localhost IPC, in-memory cross-process queue, or local persistent files.
- Only the database lease holder executes work. Shadow mode may mutate only lease/heartbeat coordination and metrics; it creates no scan cursors, queue claims, provider calls, or business mutations.
- Two-slot deadline-aware scheduling: one urgent dispatch lane plus one maintenance/general lane, one batch per job type, bounded wall time, inter-batch yields, backoff with jitter, and graceful SIGTERM.
- Admit slot two only below 70% CPU and memory. Pause new work above 85% CPU or 85% memory; warn/slow above 75% memory and resume with hysteresis.
- A dedicated protected health endpoint reports lease epoch, heartbeat, last success/failure, lag, batch duration/count, retries, pauses, cgroup CPU/memory, and worker degradation; public liveness remains coarse.
- The API health endpoint reads shared PostgreSQL state, so visibility is identical if the worker later runs on another service.
- The image health check must be topology-aware: retain HTTP liveness for the colocated web container and use process liveness in dedicated mode without a local API port or an extra database connection. Durable heartbeat freshness remains an external protected-health/alert check.

## Architecture

`src.background_worker` is a hosting-neutral composition root and the only worker command. It constructs and closes its own engine, repositories, providers, heartbeat, resource adapter, and scheduler. The controller owns dispatch and maintenance/general workload slots. Infrastructure implements bounded steps and cgroup readings. `docker-entrypoint.sh` only adapts this process to colocated supervision; a future hosted-worker service invokes the module directly. One ordinary workload DB section may run at a time while a second DB permit remains available to coordination.

## Workload Schedule Contract

| Workload | Lane | Initial state | Due/catch-up | Completion |
|---|---|---|---|---|
| Push dispatch | Urgent | Enabled at cutover | Poll for <=2m lag; always catch up | 0 due native rows |
| Trial scheduling | Maintenance | Enabled at cutover | Every 2m bucket; current-window catch-up | Final scan cursor |
| Timezone precompute | Maintenance | Enabled at cutover | First opportunity each local date | Final scan cursor |
| Cleanup | Maintenance | Enabled at cutover | Daily UTC; repeat bounded deletes | 0 eligible rows |
| Lifecycle scans | General/second slot | Disabled | Daily 09:00 UTC when later activated | Final scan cursor |
| Affiliate drain | General/second slot | Disabled | Poll for <=5m lag when later activated | 0 due native rows |

## Related Code Files

### Create

- `src/background_worker.py`
- `src/app/services/background_job_worker_service.py`
- `src/domain/ports/background_job_workload_port.py`
- `src/infra/monitoring/container_resource_monitor.py`
- `tests/unit/app/services/test_background_job_worker_service.py`
- `tests/unit/infra/monitoring/test_container_resource_monitor.py`
- `tests/unit/test_docker_entrypoint_supervision.py`

### Modify

- `docker-entrypoint.sh`
- `Dockerfile`
- `src/api/routes/v1/health.py`
- Existing dependency/container and observability registration files
- `tests/unit/api/test_health_router.py`

## Implementation Steps

1. Make `python -m src.background_worker` a standalone composition root returning meaningful process exit codes. Direct invocation requires `BACKGROUND_WORKER_ENABLED=true` and fails fast on invalid/disabled configuration instead of running a healthy no-op. It must not import/start FastAPI or Uvicorn, and must construct/close its own worker-specific database engine, providers, heartbeat, resource adapter, and scheduler. Define one minimal workload protocol returning (`completed`, `more_work`, `deferred`, `lost_lease`, `failed`) plus item count/cursor. Put orchestration in `src/app/services`; inject concrete infra workloads at the root module so import-linter boundaries remain intact.
2. Implement the schedule table and three default-false flags. Initial activation sets only `BACKGROUND_JOB_PUSH_ENABLED=true`; that flag enables all four notification steps. Dormant jobs are not scheduled or counted as due.
3. Implement a semaphore hard-capped at two plus a per-job in-flight set. Reserve one slot for due dispatch; select one overdue maintenance job for the other slot, with oldest-deadline fairness and no two maintenance jobs at once. If dispatch is idle, maintenance still remains one-at-a-time during initial rollout.
4. Run lease renewal independently with priority when due. Route every worker DB opening through the total gate; ordinary paths also use the one-permit workload gate. Enforce the single acquisition order from Phase 1, prohibit lock upgrades while holding a session, and bound acquisition/statement time below renewal safety margin. Fence claims by epoch and refuse stale completion.
5. Implement shadow mode with an explicit mutation allowlist: lease/heartbeat and metrics only. Assert no job-run cursor, notification/email/affiliate claim, cleanup, or provider call occurs.
6. Sample cgroup v2 in both hosting modes. CPU percent is `delta(usage_usec) / (delta(monotonic_usec) * (quota/period)) * 100` from `cpu.stat` and finite `cpu.max`; memory percent is `memory.current / memory.max * 100`. Use a minimum sampling interval, retain hysteresis, and fail closed for new claims on the first CPU sample, `max`/unlimited bounds, missing/malformed values, nonpositive intervals, or counter reset. Test 0.5-, 1-, and 2-CPU quotas. Admit slot two only below the soft guard; reduce to one or zero new batches as pressure rises, pause at hard limits, persist the sanitized sample/degradation snapshot, and do not kill in-flight calls. Shared-instance web p95 remains a colocated rollout gate, not worker-internal state.
7. Handle SIGTERM by stopping admission, then independently awaiting/checkpointing/releasing both possible in-flight batches within one shared grace deadline shorter than Render's. Close heartbeat, engine, and provider resources after both terminal outcomes are recorded or timed out.
8. Update `docker-entrypoint.sh` as a colocated-only adapter. Disabled mode preserves `exec uvicorn`. Enabled plus `BACKGROUND_WORKER_HOSTING_MODE=colocated` forces one Uvicorn worker, invokes the unchanged standalone worker command, forwards signals, and reaps children. Uvicorn exit terminates the container; worker exit restarts only the worker with bounded backoff while web stays serving. Reject `dedicated` mode in this web-entrypoint path so a misconfigured web service cannot silently omit Uvicorn.
9. Add `GET /v1/health/background-worker` protected by `require_monitoring_access`; read only the bounded durable PostgreSQL health snapshot/run state and expose heartbeat/snapshot freshness, hosting mode, opaque instance ID, last outcomes/lag, resource pressure, and degradation while redacting owner/error detail. Keep the last snapshot visible but explicitly stale across release/takeover until the new epoch writes. Keep `/health` and `/v1/health` unchanged and unauthenticated. Never add public pause/run-now controls or assume the worker is local.
10. Test schedule keys, lane overlap/exclusion, dormant flags, fairness, normalized cgroup-driven 2 -> 1 -> 0 admission, first/reset/bad samples, durable health takeover, and two-batch shutdown. Add a combined contention test in direct and `NullPool` modes: both workload slots active, ordinary DB gate saturated, claim lock contended, heartbeat due; prove renewal deadline, per-process worker sessions <=2, ordinary DB sections <=1, no deadlock/takeover, and continued workload progress.
11. Make the Docker health check hosting-mode aware: retain the current HTTP probe in colocated mode, but in dedicated mode check worker-process liveness without a local API port or a third database connection; monitor durable heartbeat freshness through the protected API route/alert. Add standalone process tests proving the worker boots without importing/starting FastAPI or Uvicorn, handles SIGTERM and exit codes itself, uses its own DB engine settings, and coordinates correctly when colocated- and dedicated-mode processes briefly overlap. Build one Docker image and smoke-run both `/app/docker-entrypoint.sh` and `python -m src.background_worker`; do not create a second image or service definition.

## Todo List

- [ ] Add two-slot scheduler service and executable module.
- [ ] Keep the worker executable and DB/provider lifecycle hosting-neutral.
- [ ] Implement shadow mode and resource guards.
- [ ] Encode cadence, catch-up, flags, and starvation prevention.
- [ ] Prove dispatch/maintenance overlap and per-job exclusion.
- [ ] Supervise Uvicorn and worker with correct signals/exits.
- [ ] Publish durable protected health and metrics.
- [ ] Test worker loop and shell lifecycle failure modes.
- [ ] Smoke-test the same image in colocated and standalone modes.
- [ ] Make image health checks valid without a local web port.

## Success Criteria

- [ ] Enabled colocated containers have one Uvicorn child and one worker child; disabled colocated containers behave exactly as today, while dedicated mode has only the worker process.
- [ ] A second container remains idle while a valid lease exists and takes over after expiry.
- [ ] Worker death restarts the worker with backoff while web stays available; Uvicorn death exits the container cleanly.
- [ ] SIGTERM stops new claims and exits within the configured grace window.
- [ ] Shadow mode is business-mutation-free and provider-free; only coordination/metrics writes are allowed.
- [ ] Resource pressure pauses new batches and is visible through metrics.
- [ ] Workload concurrency never exceeds two; same-job and maintenance overlap never occur.
- [ ] Heartbeat renews on time with both lanes active and claim contention, without exceeding two DB sessions per worker process.
- [ ] Moving execution to a separate hosted process requires only command/environment changes; workload code, schema, durable state, and image remain unchanged.

## Risk Assessment

- **Shell as PID 1 mishandles children:** use POSIX-compatible traps/waits and add an init process only if tests prove the existing image cannot reap reliably.
- **Worker crash-loop:** bound local restart/backoff and publish degraded health/alerts. Applying `BACKGROUND_WORKER_ENABLED=false` or a workload-flag change requires a Render deploy/restart; the old worker drains on SIGTERM, and colocated Uvicorn also restarts through the normal web deployment lifecycle.
- **Two batches harm web latency:** soft admission drops concurrency before hard gates; staging must prove two-slot execution or reduce the configured maximum to one without redesign.

## Security Considerations

Health detail remains behind existing protection, and logs/metrics contain counts and opaque IDs only. Provider/database credentials are supplied directly to the worker environment in either topology and never relayed through the API or localhost IPC. No user-triggerable arbitrary job execution is added.

## Next Steps

Phase 5 proves the two notification lanes in staging, then disables only the active push cron. Email and affiliate remain dormant pending later activation gates.
