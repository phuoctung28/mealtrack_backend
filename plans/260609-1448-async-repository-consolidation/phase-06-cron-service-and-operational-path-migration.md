---
phase: 6
title: "Cron Service and Operational Path Migration"
status: completed
priority: P2
effort: "3-5 days"
dependencies: [5]
---

# Phase 6: Cron Service and Operational Path Migration

## Overview

Migrate cron jobs, background services, health checks, and operational DB paths to async DB access.

## Requirements

- Functional: cron entrypoints use async DB engine/UoW.
- Functional: health checks use async engine/session and preserve operational signal.
- Functional: background services no longer open sync `UnitOfWork`.
- Non-functional: no scheduler contract break.

## Architecture

Cron entrypoints may stay as `async def run()` functions but must avoid sync engine warmups and sync UoW. If a platform wrapper needs sync entrypoint compatibility, it should call `asyncio.run(run())` at the outermost boundary only.

## Related Code Files

- Modify: `src/cron/push.py`
- Modify: `src/cron/email.py`
- Modify: `src/infra/services/cron_trial_push_service.py`
- Modify: `src/infra/services/cron_notification_dispatch_service.py`
- Modify: `src/infra/services/cron_lifecycle_email_service.py`
- Modify: `src/infra/services/daily_context_precompute_service.py`
- Modify: `src/api/routes/v1/health.py`
- Modify: cron and health tests

## Implementation Steps

1. Replace sync engine warmups with async engine checks.
2. Replace `with UnitOfWork()` with `async with AsyncUnitOfWork()`.
3. Convert sync query calls in cron services to async `select()` calls.
4. Preserve failure behavior: one failed notification phase should not abort all independent phases unless current behavior says so.
5. Update tests for async cron behavior.
6. Run notification/email cron and health tests.

## Success Criteria

- [x] No runtime cron/service file imports sync DB config or sync UoW.
- [x] Notification cron tests pass.
- [x] Email cron tests pass.
- [x] Health endpoint tests pass.
- [x] Scheduler entrypoint behavior remains compatible.

## Progress Notes

- `src/cron/push.py` and `src/cron/email.py` now warm up and dispose the async engine.
- `CronTrialPushService`, `CronNotificationDispatchService`, and `DailyContextPrecomputeService` now use `AsyncUnitOfWork`.
- Push dispatch, cleanup, stale-row recovery, failed-token deactivation, and batch calorie/hydration lookups are async DB work.
- Health DB connection and notification token probes now use async engine/session access.
- Removed cron, operational service, and health files from the sync DB import allowlist.

## Risk Assessment

Risk: cron services contain large sync query blocks.

Mitigation: migrate service by service and keep tests close to current failure semantics.
