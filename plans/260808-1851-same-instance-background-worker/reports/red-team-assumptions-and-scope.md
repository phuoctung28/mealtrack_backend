# Red-Team Assumptions and Scope Review

## Scope

- Reviewed `plan.md`, all five phase files, both research reports, and the approved brainstorm.
- Inspected cron entrypoints, notification/email/affiliate services and models, settings, DB runtime, migration graph, Docker lifecycle, health/observability, tests, CI, and evergreen docs.
- Two-pass result: **9 blocking findings, 1 informational finding**.
- Verdict: **plan is not implementation-ready**. Approved hosting, batch ceilings, resource thresholds, and no-new-infrastructure decisions remain unchanged.

## Pass 1 — Blocking Findings

### F1 — Critical — Plan silently reverses the approved cutover order

- **Plan location:** `phase-05-verification-and-staged-cron-cutover.md:63-65`
- **Evidence:** The approved decision is affiliate, then email, then push in `plans/reports/260808-1848-same-instance-background-worker-brainstorm.md:141-149`. The phase instead moves push first, affiliate second, and email last.
- **Invalid assumption / scope gap:** A later research preference was promoted over a user-approved rollout decision without new production evidence. None of the research reports contains a benchmark or incident result that justifies reversing the approved order.
- **Impact:** Review/audit drift; rollout risk and rollback sequencing no longer match the approved contract.
- **Minimal plan correction:** Restore affiliate -> lifecycle email -> complete push-cron bundle. If the order is intentionally changing, mark it as a user decision requiring explicit approval rather than an implementation detail.

### F2 — Critical — Disabling the push cron before enabling trial scheduling creates a delivery gap

- **Plan location:** `phase-05-verification-and-staged-cron-cutover.md:63,65`
- **Evidence:** `src/cron/push.py:94-103` runs trial reminder scheduling inside the same push cron as precompute and dispatch. The plan disables the push cron at line 63, then enables trial reminders later at line 65.
- **Invalid assumption / scope gap:** The plan treats trial reminders as if they have their own matching Render cron. They do not; `src/cron/` contains only `push.py`, `email.py`, and `affiliate_outbox.py`, and the push process owns all four notification phases (`src/cron/push.py:67-132`).
- **Impact:** Trial-expiry notification rows are not created during the interval between those stages; this is silent customer-facing loss, not merely lag.
- **Minimal plan correction:** Treat precompute, trial scheduling, dispatch, and cleanup as one cutover unit. Enable all four bounded worker steps and prove them healthy before disabling the single push cron.

### F3 — Critical — Staged rollout and rollback require per-workload flags that the implementation phases never define

- **Plan location:** `phase-01-durable-runtime-foundation.md:63-64`; `phase-04-sibling-worker-and-process-supervision.md:62`; `phase-05-verification-and-staged-cron-cutover.md:63-66`
- **Evidence:** The approved design explicitly requires per-job feature flags (`plans/reports/260808-1848-same-instance-background-worker-brainstorm.md:163-175`). Phase 1 defines only generic worker enabled/shadow settings and batch sizes. Phase 4 registers all workloads in one list. The current settings surface contains no background-worker fields (`src/infra/config/settings.py:17-23` onward), and `.env.example:49-61` only documents Uvicorn/DB-pool controls.
- **Invalid assumption / scope gap:** Phase 5 assumes individual notification, affiliate, trial, and email paths can be enabled and disabled, but no exact config names, defaults, validation, or registry gating are specified.
- **Impact:** The stated one-workload-at-a-time rollout and per-workload rollback cannot be executed safely; operators would have only a global kill switch.
- **Minimal plan correction:** Add exact default-false per-workload settings in Phase 1 and `.env.example`, then require Phase 4 registry gating and tests for every flag. The push cron's four internal steps should share one cutover flag or an explicitly validated all-four combination.

### F4 — Critical — Notification owner-checked completion is impossible with the current schema, but no migration is planned

- **Plan location:** `phase-02-bound-notification-workloads.md:34-35,65,69`; Related Code Files at `:42-59`
- **Evidence:** `NotificationORM` has status but no claim owner or claim timestamp/lease (`src/infra/database/models/notification/notification.py:34-45`). Existing completion/retry updates check only `status = 'processing'` (`src/infra/services/cron_notification_dispatch_service.py:250-284`). Phase 2 requires an owner token on every result mutation but lists no notification model or migration change.
- **Invalid assumption / scope gap:** A scheduler-level lease cannot prove row-level ownership after claim commit, lease loss, or stale reclaim. The row has nowhere to persist the owner token the plan requires.
- **Impact:** A stale worker can mark rows sent/failed after a new owner reclaimed them; concurrent cron/worker overlap is not safely owner-conditional, violating a core cutover guarantee.
- **Minimal plan correction:** Add a Phase 2 notification-claim migration/model change with owner token and claim/lease timestamp plus reclaim index, or specify an equivalent durable row-to-run ownership relation. Include old-owner rejection and stale-reclaim integration tests.

### F5 — High — Affiliate ownership migration is known to be required, not conditional

- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:54-59,66-67`
- **Evidence:** The model contains only `status`, `locked_at`, and retry fields (`src/infra/database/models/affiliate_event_outbox.py:26-31`). Claiming leaves status `pending` and writes only `locked_at` (`src/infra/repositories/affiliate_event_outbox_repository.py:47-70`); completion/failure mutations have no owner predicate (`:72-96`). The current migration has no owner or lease-expiry columns (`migrations/versions/20260610000001_add_affiliate_event_outbox.py:19-46`).
- **Invalid assumption / scope gap:** The phase says to create a revision "only if" the table lacks required fields, but repository inspection already proves it lacks them.
- **Impact:** Implementers can incorrectly skip the migration, leaving the documented concurrent-double-claim defect in production.
- **Minimal plan correction:** Make the affiliate ownership migration mandatory in Related Code Files, based on the verified current head. Specify owner token, processing state, lease expiry, constraints/indexes, and safe backfill/default behavior.

### F6 — High — Batching does not remove the precompute N+1 query path

- **Plan location:** `phase-02-bound-notification-workloads.md:63,69`
- **Evidence:** Precompute loops over every selected user and awaits `_get_user_calorie_goal` (`src/infra/services/daily_context_precompute_service.py:598-614`). Each call performs a weekly-budget lookup (`:413-416`); for existing budgets it calls `WeeklyBudgetService.get_effective_adjusted_daily_async` (`:430-442`), which performs per-user cheat-day, daily-count, meal-range, and movement queries (`src/domain/services/weekly_budget_service.py:440-504`, `:117-220`).
- **Invalid assumption / scope gap:** Limiting a page to 100 users bounds memory but still produces at least 100 extra DB queries and often several hundred per step. The plan says dependent data is loaded for the batch but does not cover this existing per-user call chain.
- **Impact:** The same-instance worker can saturate DB/CPU and regress API latency even after the OOM is fixed; a 100-user batch is not a meaningful load ceiling for query work.
- **Minimal plan correction:** Add a Phase 2 requirement to batch-load weekly budgets and weekly consumption inputs for the page, or explicitly lower/yield based on a measured query budget. Add a query-count regression test for a full 100-user page.

### F7 — High — Planned PostgreSQL concurrency tests bypass the existing CI PostgreSQL job

- **Plan location:** Phase 1 `phase-01-durable-runtime-foundation.md:49-50`; Phase 2 `phase-02-bound-notification-workloads.md:57-59`; Phase 3 `phase-03-harden-email-and-affiliate-delivery.md:57-59`
- **Evidence:** New real-Postgres tests are assigned to `tests/integration/infra/repositories/`. CI runs only `tests/integration/postgres` (`.github/workflows/ci.yml:80-132`), while default pytest ignores all integration tests (`pytest.ini:11-19`). Evergreen testing docs confirm the PostgreSQL CI scope (`docs/testing-standards.md:61-78`).
- **Invalid assumption / scope gap:** Phase 5's manual command does not make these race-condition tests continuous regression gates.
- **Impact:** The highest-risk lease/claim tests can pass during implementation and then silently stop running in CI.
- **Minimal plan correction:** Put PostgreSQL lease/claim/concurrency tests under `tests/integration/postgres/`, or explicitly modify `.github/workflows/ci.yml` to include their chosen path and marker.

### F8 — High — The resource-pause requirement has no usable container-level measurement design

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:29,36,64-65`
- **Evidence:** The phase correctly admits worker RSS is insufficient because Uvicorn is a sibling (`:29`), but then requires the worker to pause on 85% CPU/memory (`:36`) without naming a container/cgroup reader, dependency, sampling window, or unavailable-metric behavior. The existing runtime exposes DB pool values, not container CPU/memory (`src/api/routes/v1/health.py:80-117`); no `psutil` or resource monitor exists in `requirements.txt`/`src` (verified by `rg`).
- **Invalid assumption / scope gap:** Render dashboard metrics are an operator telemetry source, not an in-process control input. Process-only measurements cannot enforce the approved whole-instance thresholds.
- **Impact:** The advertised safety brake either measures the wrong denominator, never triggers, or requires unplanned platform-specific code; shared-instance OOM/latency protection remains unproven.
- **Minimal plan correction:** Specify a minimal Linux cgroup/container measurement adapter (with process fallback explicitly marked degraded), sampling interval/window, hysteresis, and fail-open/fail-closed behavior. Keep Render metrics as the cutover authority.

### F9 — High — Supervision behavior contradicts the Phase 5 availability criterion

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:41,67,83`; `phase-05-verification-and-staged-cron-cutover.md:84`
- **Evidence:** Phase 4 requires either child death to terminate the surviving child and exit the container. Phase 5 simultaneously requires the web service to remain available through worker crash. On a single instance, intentionally killing Uvicorn is not web availability; it is restart-based recovery.
- **Invalid assumption / scope gap:** The success criterion conflates controlled restart with uninterrupted availability.
- **Impact:** A Docker smoke test cannot honestly satisfy both conditions, and acceptance can be declared incorrectly.
- **Minimal plan correction:** Preserve the approved whole-container restart decision, but rewrite the Phase 5 gate to measure controlled Render recovery/readiness within an explicit time bound. If uninterrupted availability is required instead, that is a separate supervision decision requiring approval.

## Pass 2 — Informational Finding

### F10 — Medium — The file/test/doc map was not fact-checked against the repository

- **Plan location:** Phase 1 `phase-01-durable-runtime-foundation.md:16-18,54-56`; Phase 2 `phase-02-bound-notification-workloads.md:16-18,46-53`; Phase 3 `phase-03-harden-email-and-affiliate-delivery.md:49`; Phase 4 `phase-04-sibling-worker-and-process-supervision.md:19,58`; Phase 5 `phase-05-verification-and-staged-cron-cutover.md:16,50-53`
- **Evidence:** `src/core/config.py`, `src/infra/database/database.py`, all three Phase 2 domain-service paths, `notification_repository.py`, `user_repository.py`, `firebase_notification_adapter.py`, `email_port.py`, `src/infra/observability/`, `tests/unit/api/routes/v1/test_health.py`, and `docs/deployment-guide.md` do not exist. Actual anchors include `src/infra/config/settings.py:17`, `src/infra/database/config_async.py:1`, `src/infra/services/daily_context_precompute_service.py:39`, `src/infra/services/cron_notification_dispatch_service.py:1`, `src/domain/ports/email_service_port.py:16`, `docs/system-architecture.md:90-93`, and `tests/unit/api/test_health_router.py:1-4`.
- **Invalid assumption / scope gap:** The plan labels non-existent files as current context/modify targets rather than create targets or discovery placeholders.
- **Impact:** Implementation effort, ownership, architecture placement, and test updates are understated; an implementer can create parallel abstractions instead of modifying the actual runtime.
- **Minimal plan correction:** Replace every stale path with the actual file. Mark `docs/deployment-guide.md` as Create or remove it in favor of the new runbook. Add `tests/unit/infra/database/test_model_registry_metadata.py` to Phase 1 model-registry coverage.

## Verified Non-Findings

- **Cron inventory is otherwise complete:** repository has exactly three Render cron entrypoints: push, lifecycle email, and affiliate outbox. `web_funnel_outbox_dispatch_service.py` is request-triggered from `src/api/routes/v1/webhooks.py:120-128`, not a fourth Render cron.
- **Migration base is correct:** fresh `alembic heads` returned `20260807000002 (head)`, matching `plan.md:54` and Phase 1.
- **Resend SDK claim is correct:** pinned `resend==2.30.1` (`requirements.txt:62`) exposes `Emails.send(params, options)` and accepts `idempotency_key` in the options object.
- **Render overlap/shutdown premise is current:** [official Render deploy docs](https://render.com/docs/deploys) confirm old/new instance overlap, SIGTERM, a default 30-second shutdown delay, and a configurable maximum of 300 seconds.

## Behavioral Checklist

- Concurrency: lease loss, row ownership, stale reclaim, cron/worker overlap checked.
- Error boundaries: external-call ambiguity, worker/child failure, and shutdown behavior checked.
- API contracts: email port and health protection paths checked.
- Backwards compatibility: cron wrappers, email callers, model/migration changes checked.
- Input/config validation: settings names/defaults, flag granularity, TTL/resource validation checked.
- Auth/authz: no new public worker control plane planned; protected monitoring dependency exists at `src/api/routes/v1/health.py:80-81`.
- N+1/query efficiency: precompute weekly-budget chain checked.
- Data leaks: plan's sanitized errors/opaque IDs align with existing observability policy; no new leak finding.
- Fact-check: paths, migration head, cron inventory, models, ports, callers, CI paths, and docs verified with repository search.

## Unresolved Questions

- Which existing telemetry source will supply the approved API p95 gate? Render's [standard service metrics](https://render.com/docs/service-metrics) document p50/p75/p90/p99; p95 is available through [Pro metrics streaming](https://render.com/docs/metrics-streams), while the repo has sampled Sentry tracing but no named p95 query (`src/infra/config/settings.py:187-198`, `src/api/middleware/request_logger.py:66-80`). This should be resolved in the rollout runbook before cutover, without changing the 20% threshold.

**Status:** DONE_WITH_CONCERNS
**Summary:** Hard-mode review found 9 blocking assumption/scope defects and 1 informational code-map defect. Approved architecture remains viable after plan corrections.
**Concerns/Blockers:** Lost trial reminders during current cutover sequence, missing per-workload controls, missing row-ownership schema, N+1 query pressure, and concurrency tests outside CI.
