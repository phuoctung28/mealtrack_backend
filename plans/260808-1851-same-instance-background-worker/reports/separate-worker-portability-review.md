# Separate Worker Portability Review

## Assessment

The initial review found five implementation-readiness gaps. The approved topology itself remained sound: one Render Standard web instance initially, one image, `python -m src.background_worker`, notification-only activation, dormant email/affiliate jobs, and no separate service provisioned now.

## Blocking Findings

### High — Worker DB isolation is not implementable through the current “factory” seam

- `phase-01-durable-runtime-foundation.md:71` says to extend the existing async-engine factory without reusing the API engine, but `src/infra/database/config_async.py:14,66-125` loads environment state and creates API engine/session globals at import. Reused workloads also transitively bind to those globals (`src/infra/database/uow_async.py:13,97-110`; `src/infra/services/affiliate_outbox_dispatch_service.py:7,21-32,48`). A standalone worker can therefore create/use the API engine outside its worker settings, two-permit gate, and cleanup lifecycle.
- **Minimal correction:** require a side-effect-free policy/engine/session-factory builder taking explicit worker settings. Keep API globals as a compatibility wrapper only. Inject the worker session/UoW factory into every worker workload and route every session through the worker gate. Test that standalone startup creates exactly one worker-configured engine, does not initialize/import the API DB singleton path, and closes that engine on every exit.

### High — The PostgreSQL schema does not carry the durable health contract

- The amendment requires health in PostgreSQL (`reports/separate-hosted-worker-portability-amendment.md:18-23`), and Phase 4 requires the API to report last success/failure, lag, batch count/duration, retries, pauses, cgroup samples, and degradation from durable state (`phase-04-sibling-worker-and-process-supervision.md:39-41,88`). Phase 1's lease/run schema lists no durable fields for pauses, resource samples, degradation, or queue-drain batch outcomes; queue drains intentionally have no aggregate run row (`phase-01-durable-runtime-foundation.md:22,35,43,66-67`). Those values cannot be reconstructed after a service handoff.
- **Minimal correction:** add a bounded, sanitized health snapshot to the lease-group row (or one dedicated health row) with owner/epoch-fenced updates for per-workload outcome/lag/count/duration plus resource/degradation state. Preserve the last snapshot across release/takeover, expose freshness separately, and test API visibility before, during, and after colocated-to-dedicated takeover.

### High — Rollback is written as a live flag toggle, but flags are startup-cached

- Phase 5 says to set the push flag false, then wait for both slots to drain before re-enabling cron (`phase-05-verification-and-staged-cron-cutover.md:66`); Phase 4 calls disabling the worker an immediate rollback “without killing healthy Uvicorn” (`phase-04-sibling-worker-and-process-supervision.md:120`). Current settings are process-global and cached (`src/infra/config/settings.py:383-389`). A Render environment change requires a new container/process, so the documented sequence cannot observe the old process draining in place and will restart the colocated web process.
- **Minimal correction:** define rollback as a restart/deploy operation: deploy colocated config with push execution false, let the old worker receive SIGTERM and checkpoint/release within grace, verify durable claims/lease show execution stopped, then re-enable cron. State explicitly that colocated rollback restarts Uvicorn; do not imply live reload. Apply the same disable-drain-verify-enable ordering to the future dedicated-to-colocated reversal.

### High — The two-DB-permit contract is per process, but overlap budgeting is unstated

- Phase 1 defines in-process semaphores and a two-session worker cap (`phase-01-durable-runtime-foundation.md:28,71-72`), while the topology handoff deliberately overlaps colocated and dedicated contenders (`phase-05-verification-and-staged-cron-cutover.md:69-70`). Each contender can consume its own coordination sessions, and the API independently owns its pool (`src/infra/database/config_async.py:69-125`; `src/infra/database/connection_policy.py:105-134`). PostgreSQL fencing prevents duplicate ownership, not aggregate connection use.
- **Minimal correction:** state that two permits are **per worker process**. Add an overlap connection-budget gate covering API pools plus every old/new worker contender, measured against the provider limit, and block deploy/handoff if the budget fails. Keep workload execution lease-fenced; do not add a distributed permit service.

### High — Cgroup CPU percentages are not defined

- Phase 4 makes 70%/85% admission decisions from `cpu.stat`/`cpu.max` in both modes (`phase-04-sibling-worker-and-process-supervision.md:38,85`), but these files expose a cumulative usage counter and quota/period, not a percentage. No sampling interval/normalization or handling is defined for `max`, first sample, counter reset, or malformed values. A plausible implementation can permanently close slot two or admit it under saturation.
- **Minimal correction:** specify CPU utilization as the delta of cgroup usage over a monotonic interval normalized by the `cpu.max` quota/period; specify memory as `memory.current / memory.max`. Define fail-closed behavior for unlimited/missing/malformed/counter-reset states and test 0.5/1/2-CPU quotas, first sample, hysteresis, and both hosting modes.

## Verified Non-Blockers

- Existing-cron overlap is covered by the shared bounded notification methods/claims and an explicit concurrent worker/cron ownership test (`phase-02-bound-notification-workloads.md:66-73,89-96`).
- The future handoff uses the same image/schema/workload code and direct worker command; dedicated provisioning remains deferred (`reports/separate-hosted-worker-portability-amendment.md:25-38`).
- Email and affiliate remain false-flagged with zero claims/provider calls, and initial capacity evidence is notification-only (`phase-05-verification-and-staged-cron-cutover.md:37,64,67,93`).
- The maximum-two workload contract remains urgent dispatch plus one mutually exclusive maintenance batch; the DB-permit clarification above does not change that approved limit.

## Unresolved Questions

None. The corrections are implementation contracts, not new product or hosting decisions.

## Revalidation After Plan Corrections

1. **PASS — worker DB isolation.** Phase 1 now requires a side-effect-free explicit-settings engine/session/UoW builder, API globals only as wrappers, injected worker factories for every workload, one worker engine, and closure tests (`phase-01-durable-runtime-foundation.md:72,75`). The portability amendment repeats the runtime and validation contract (`reports/separate-hosted-worker-portability-amendment.md:22,45-47`).
2. **PASS — durable health.** The lease schema now includes a bounded sanitized, owner/epoch-fenced health snapshot preserved across release/takeover (`phase-01-durable-runtime-foundation.md:43,67,75,96`). The protected API explicitly distinguishes stale and fresh snapshots across epochs (`phase-04-sibling-worker-and-process-supervision.md:88-89`).
3. **PASS — restart-based rollback.** The plan now states that environment changes deploy/restart the colocated web service and drain the old worker through SIGTERM (`phase-04-sibling-worker-and-process-supervision.md:120`; `phase-05-verification-and-staged-cron-cutover.md:67,70,97`). No live flag reload is assumed.
4. **PARTIAL — aggregate DB budgeting still omits a valid `NullPool` API bound.** The plan correctly declares two permits per worker process and adds an overlap budget (`phase-01-durable-runtime-foundation.md:28`; `phase-05-verification-and-staged-cron-cutover.md:39,63,70`). However, its formula uses overlapping API “pool capacities.” In supported `neon_pooler` mode the live policy reports pool capacity as zero (`src/infra/database/connection_policy.py:29-33,115-124`), while API sessions can still open concurrent PgBouncer client connections and have no process-wide API session gate (`src/infra/database/config_async.py:90-125`). The gate can therefore undercount the API contribution during old/new overlap.
   - **Remaining minimal correction:** define API contribution by mode: configured `worker_count * (pool_size + max_overflow)` per overlapping direct-pool instance; for `NullPool`, an explicit enforced API session/concurrency ceiling or conservative measured peak plus stated headroom—never zero. Add budget-calculation tests for both modes.
5. **PASS — cgroup normalization.** Phase 4 now defines the CPU delta/quota formula, monotonic interval, memory ratio, fail-closed states, hysteresis, and 0.5/1/2-CPU tests (`phase-04-sibling-worker-and-process-supervision.md:85,89`).

The adjudication and validation reports accurately record the four full resolutions and the intended fifth correction (`reports/red-team-adjudication.md:44-52`; `reports/plan-validation.md:21-37`), but they overlook the live `NullPool.total_capacity == 0` behavior above. Current Render documentation also supports the plan's separate-service assumption: background workers are continuous non-ingress services and Docker services can override the image `CMD`.

## Final NullPool Budget Revalidation

**PASS.** The remaining blocker is resolved:

- Direct mode budgets every overlapping API instance as `UVICORN_WORKERS * (pool_size + max_overflow)` (`phase-05-verification-and-staged-cron-cutover.md:63`).
- `neon_pooler`/`NullPool` explicitly ignores policy `total_capacity=0` and budgets each overlapping API instance as `max(10, ceil(1.5 * observed_service_peak))`, using a representative 24-hour/midnight maximum (`phase-05-verification-and-staged-cron-cutover.md:63`; `reports/separate-hosted-worker-portability-amendment.md:38`).
- Both formulas add two permits per overlapping worker and an operational/migration reserve of `max(10, ceil(20% * provider_limit))` (`phase-05-verification-and-staged-cron-cutover.md:63`).
- Missing telemetry, missing provider limits, zero contribution, or an over-limit result blocks rollout (`phase-05-verification-and-staged-cron-cutover.md:63`; `reports/separate-hosted-worker-portability-amendment.md:55`).
- Named unit coverage includes both modes, zero/absent pooler capacity, rounding, headroom, and rejection paths (`phase-05-verification-and-staged-cron-cutover.md:63`).

No portability blocker remains. Runtime capacity and cgroup availability remain explicit Phase 5 evidence gates, not unresolved design gaps.

**Status:** DONE
**Summary:** All five portability blockers are implementation-ready after final direct/NullPool budget correction.
**Concerns/Blockers:** None.
