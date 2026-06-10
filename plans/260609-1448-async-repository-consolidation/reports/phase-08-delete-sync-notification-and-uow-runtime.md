# Phase 8 Report: Delete Sync Notification and UoW Runtime

## Summary

Removed the sync notification runtime path and sync UnitOfWork runtime. Cron dispatch now owns stale-processing reclaim timing directly, notification persistence is async-only, and app handlers type against `AsyncUnitOfWorkPort`.

## Files Changed

- Deleted: `src/infra/repositories/notification_repository.py`
- Deleted: `src/infra/repositories/notification/reminder_query_builder.py`
- Deleted: `src/infra/database/uow.py`
- Deleted: `src/domain/ports/unit_of_work_port.py`
- Updated: `src/infra/services/cron_notification_dispatch_service.py`
- Updated: `src/infra/database/uow_async.py`
- Updated: command/query/event handlers that still referenced `UnitOfWorkPort`
- Deleted stale sync-only notification tests:
  - `tests/unit/test_notification_repository.py`
  - `tests/unit/infra/test_notification_queries.py`
  - `tests/integration/test_timezone_aware_notifications.py`

## Verification

- `pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/database/test_uow_meal_suggestion_boundary.py -q`
  - Result: `37 passed`
- Expanded async repository consolidation bundle:
  - Result: `248 passed, 3 warnings`
- Full suite:
  - `pytest -q`
  - Result: `1533 passed, 3 skipped, 11 warnings`
- Touched-file lint:
  - `ruff check src/infra/database/uow_async.py src/infra/services/cron_notification_dispatch_service.py src/domain/ports/notification_repository_port.py src/domain/utils/timezone_utils.py tests/test_setup.py tests/unit/api/test_webhook_handler.py tests/unit/infra/test_daily_context_precompute_service.py tests/architecture/test_async_db_runtime_boundaries.py tests/integration/api/conftest.py tests/fixtures/fakes/fake_notification_repository.py tests/fixtures/fakes/fake_uow.py`
  - Result: `All checks passed`

## Boundary

The request/runtime sync UoW and notification selector path are gone. Remaining sync ORM repository files are test-coupled legacy implementations on the architecture allowlist, not imported by request runtime wiring.

## Unresolved Questions

None.
