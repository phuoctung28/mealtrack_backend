---
phase: 5
title: "Verification and Staged Cron Cutover"
status: pending
priority: P1
effort: "1-2 days plus observation windows"
dependencies: [4]
---

# Phase 5: Verification and Staged Cron Cutover

## Context Links

- [Overview](./plan.md)
- [Batching and rollout research](./research/researcher-02-batching-delivery-and-rollout.md)
- `docs/testing-standards.md`
- Render dashboard for the existing web and cron services

## Overview

Verify logic, two-slot process behavior, and the standalone hosting seam locally, then migrate the only active workload: the complete notification bundle. Email and affiliate stay disabled and are excluded from initial capacity evidence. The active push cron is removed only after midnight observation and rollback proof; no separate worker service is provisioned in this rollout.

## Key Insights

- There is no repository `render.yaml`; cron removal and service environment changes are controlled through Render, so a precise runbook and evidence log are required.
- Local tests cannot prove CPU, memory, or web p95 on a shared Standard instance. These are staging/production telemetry gates.
- Midnight is the known failure window. Final acceptance requires observing that window with notification precompute enabled.

## Requirements

- Default CI-aligned tests pass: `pytest tests/unit --cov=src --cov-fail-under=65`; add focused PostgreSQL integration and migration checks.
- `ruff format --check`, `ruff check`, and `mypy src/` pass for changed areas according to repository policy.
- Docker smoke tests prove disabled mode, enabled sibling mode, worker-only restart, Uvicorn-failure exit, signal handling, lease takeover, and health visibility.
- No matching cron is disabled until the worker path is healthy and observable; no cron service is deleted until rollback has been exercised and observation gates pass.
- Record baseline and post-enable web p95, CPU, memory, DB connections, job lag, successes/failures/retries, and duplicate indicators.
- Prove maximum concurrency two, dispatch-plus-maintenance overlap, one batch per job type, and automatic admission reduction under pressure.
- Keep `BACKGROUND_JOB_EMAIL_ENABLED=false` and `BACKGROUND_JOB_AFFILIATE_ENABLED=false` throughout the initial rollout.
- Prove a later separately hosted worker can use the same image, standalone command, schema, claims, and health state; provisioning that service remains future work.
- Treat the two DB permits as per worker process and approve a mode-specific, nonzero peak API plus old/new-worker connection budget before any deploy overlap or topology handoff.

## Architecture

Deployment moves through coordination-only shadow, then notification execution with two bounded lanes. PostgreSQL ownership makes brief worker/push-cron overlap safe. Rollback deploys `BACKGROUND_JOB_PUSH_ENABLED=false`; SIGTERM drains the old worker, durable state confirms claims stopped, and only then is the push cron re-enabled. The same fencing contract supports a later handoff from colocated to separately hosted execution. Dormant jobs require separate future activation evidence.

## Related Code Files

### Create

- `docs/runbooks/background-worker-rollout.md`

### Modify

- `docs/system-architecture.md`
- `docs/codebase-summary.md`
- `docs/testing-standards.md`
- Focused unit/integration tests introduced in Phases 1-4

## Implementation Steps

1. Run focused tests after each phase, then `pytest tests/unit --cov=src --cov-fail-under=65`. Put real PostgreSQL lease/claim tests under `tests/integration/postgres/` so the existing CI job discovers them; avoid bare unscoped `pytest`.
2. Against disposable PostgreSQL, upgrade from `20260807000002` through each new revision, downgrade explicitly back to `20260807000002`, and upgrade to head. Assert runtime, notification-claim, and affiliate-claim objects/indexes at each boundary and preserve existing queue data.
3. Run `ruff format --check src/ tests/`, `ruff check src/ tests/`, `mypy src/`, and `lint-imports`. Build one image and smoke-test the colocated entrypoint plus the standalone worker command, two slots, same-job exclusion, two total/one ordinary DB permit per worker process, heartbeat-priority contention with lock-order assertions, lease takeover across hosting modes, two-batch SIGTERM, worker restart, normalized cgroup pressure, both DB modes, and durable protected health before/during/after takeover.
4. Write the rollout runbook with exact flags/values, two-lane ownership matrix, dashboards/queries, operator, commands, gates, rollback, and evidence table. Force one Uvicorn worker, two total DB permits per worker process, one ordinary-workload permit, 70% slot-two admission, heartbeat-priority claim ordering, and a named p95 source/query before cutover. Document that the colocated web service uses `BACKGROUND_WORKER_HOSTING_MODE=colocated`. For `direct_pool`, budget each overlapping API instance as `UVICORN_WORKERS * (pool_size + max_overflow)`. For `neon_pooler`/`NullPool`, never use policy `total_capacity=0`: record the maximum concurrent API client connections over the representative 24-hour/midnight baseline and budget each overlapping API instance as `max(10, ceil(1.5 * observed_service_peak))`; using the whole single-instance service peak for every contender is intentionally conservative. Add `2 * overlapping worker processes` and an operational/migration reserve of `max(10, ceil(20% * provider_limit))`. Compare direct mode with database `max_connections` and pooler mode with the provider's client-connection limit; block if telemetry/limit is unavailable or the budget does not fit. Unit-test both formulas, zero/absent pooler policy capacity, rounding, headroom, and rejection paths.
5. Capture at least 24 hours of baseline metrics. Deploy with worker enabled in shadow mode and all execution flags false; prove the mutation allowlist (lease/heartbeat/metrics only) while lag metrics populate.
6. Enable only `BACKGROUND_JOB_PUSH_ENABLED`. During safe overlap, prove dispatch runs concurrently with at most one of precompute/trial/cleanup; maintenance jobs remain mutually exclusive and email/affiliate produce zero claims/provider calls.
7. Disable the push cron only after all four notification steps are healthy. Observe a timezone-midnight run. Gate: CPU <85%, memory <75% normal/<85% peak, p95 regression <=20%, push lag <=2 minutes, concurrency <=2, no same-job overlap, starvation, backlog, stale-recipient send, cleanup race, or unexplained duplicate.
8. Drill notification rollback as a deployment operation: change colocated config to `BACKGROUND_JOB_PUSH_ENABLED=false` and deploy. The old container's worker must receive SIGTERM, stop admission, checkpoint/release both slots within grace, and exit; the colocated Uvicorn process also restarts through Render's normal web deploy. Verify durable health/claims show worker execution stopped before re-enabling the push cron, confirm durable resume, then restore the approved state. Do not imply live environment reload or downgrade schema.
9. Keep email and affiliate flags false and record them as dormant—not failed cutovers. Before either later activation, repeat workload-specific baseline, shadow/claim, delivery, resource, and rollback gates; do not infer capacity from notification results.
10. After notification passes its observation window, remove only the obsolete push cron service. Keep its compatibility module for one release; dormant email/affiliate modules and flags remain available but inactive.
11. Add a future topology-migration section to the runbook: first pass the aggregate connection-budget gate, then create a separately hosted worker from the same image/commit with start command `python -m src.background_worker`; copy worker/provider/DB settings; set `BACKGROUND_WORKER_HOSTING_MODE=dedicated`; start it in shadow with all workload flags false as a standby. Deploy the web service with its colocated worker disabled; the old worker drains/releases on SIGTERM while Uvicorn follows normal deploy restart. Verify the protected health route changes from a stale old snapshot to a fresh dedicated-instance heartbeat before deploying the dedicated push flag true. Permit brief process overlap only through the shared lease/fencing contract. Roll back with the same restart-based disable -> drain/verify -> enable ordering, never a live flag toggle. Require no migration, queue conversion, workload-code change, or second image.
12. Exercise that handoff locally or in an ephemeral environment with two worker processes sharing disposable PostgreSQL; prove exactly one lease owner, protected health visibility, clean takeover, and unchanged schema. This validates the seam only and does not provision or cut over a paid service.
13. Update evergreen architecture, testing, and codebase docs only with verified results. Do not use `docs/archive/**` roadmap/changelog as authority. Attach command output and redacted Render evidence to the deployment record, not source files.

## Todo List

- [ ] Pass unit, concurrency, migration, lint, type, and Docker checks.
- [ ] Publish executable rollout/rollback runbook.
- [ ] Establish baseline and verify shadow mode.
- [ ] Prove two notification lanes and resource-driven admission.
- [ ] Cut over the complete push bundle and observe midnight.
- [ ] Exercise notification rollback.
- [ ] Verify the config-only colocated-to-dedicated handoff seam.
- [ ] Approve aggregate API/worker deploy-overlap connection capacity.
- [ ] Confirm email and affiliate remain dormant.
- [ ] Delete only the active push cron after all gates pass.
- [ ] Synchronize evergreen project documentation.

## Success Criteria

- [ ] All automated validation commands pass with evidence recorded.
- [ ] The web service stays available through worker-child restart/backoff; Uvicorn failure yields controlled container restart.
- [ ] Shared-instance CPU, memory, database connection, and web p95 gates pass during representative load and midnight execution.
- [ ] Push delivery SLA passes while dispatch overlaps bounded maintenance.
- [ ] Notification rollback succeeds without data loss or schema rollback.
- [ ] The active push cron is removed; dormant email/affiliate flags stay false with zero claims/provider calls.
- [ ] A standalone worker from the same image takes over through PostgreSQL fencing without schema or workload-code changes.
- [ ] Rollback and topology handoff use explicit restart/drain/fresh-heartbeat ordering with no assumed live environment reload.

## Risk Assessment

- **Threshold cannot be proven locally:** block production cutover until Render metrics cover representative traffic and midnight behavior.
- **Cron/worker overlap causes ambiguity:** use the same claims/schedule keys, label every run with executor identity, and keep overlap brief.
- **Rollback replays completed work:** completed deterministic schedule keys and queue statuses remain authoritative across executor changes.

## Security Considerations

Runbook screenshots and evidence must redact environment secrets, device tokens, recipient addresses, and payloads. Render access follows existing least-privilege practice; operational controls are configuration changes, not public endpoints.

## Next Steps

After verified notification cutover, open separate activation work only when email or affiliate is actually scheduled to run; do not enable either from this rollout's capacity evidence.
