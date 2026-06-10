# Phase 6 Cron Operational Async Slice Report

## Summary

Migrated cron entrypoints, notification cron services, daily notification precompute, and health DB probes away from sync database runtime.

## Changes

- `src/cron/push.py`
  - Uses `async_engine` for warm-up, timezone lookup, and disposal.
  - Awaits trial-push scheduling and notification cleanup directly.
- `src/cron/email.py`
  - Uses `async_engine` for warm-up and disposal.
- `src/infra/services/cron_trial_push_service.py`
  - Uses `AsyncUnitOfWork`.
  - Awaits subscription, preference, token, and insert operations.
- `src/infra/services/cron_notification_dispatch_service.py`
  - Uses `AsyncUnitOfWork` for claim, mark, cleanup, stale recovery, failed-token deactivation, and batch data fetches.
  - Preserves skip-locked claiming and stale-processing recovery semantics.
- `src/infra/services/daily_context_precompute_service.py`
  - Uses `AsyncUnitOfWork`.
  - Reuses async weekly-budget calculation for calorie-goal adjustment.
- `src/api/routes/v1/health.py`
  - Uses async engine/session DB probes.
- `tests/architecture/test_async_db_runtime_boundaries.py`
  - Removes cron, operational service, and health files from the sync DB import allowlist.

## Verification

- `.venv/bin/pytest tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py -q`
- `.venv/bin/ruff check src/cron/push.py src/cron/email.py src/infra/services/cron_trial_push_service.py src/infra/services/cron_notification_dispatch_service.py src/infra/services/daily_context_precompute_service.py src/api/routes/v1/health.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py`

## Boundary

Sync notification repositories and query-builder helpers still exist for legacy tests and repository migration phases, but cron and health runtime paths no longer import sync DB config or sync UoW.

## Unresolved Questions

None.
