# Phase 2 Async Contracts Report

## Summary

Completed async contract consolidation for domain repository ports and the async Unit of Work boundary.

## Changes

- Converted repository ports to async-shaped contracts:
  - `src/domain/ports/meal_repository_port.py`
  - `src/domain/ports/user_repository_port.py`
  - `src/domain/ports/subscription_repository_port.py`
  - `src/domain/ports/saved_suggestion_repository_port.py`
  - `src/domain/ports/notification_repository_port.py`
- Added repository attributes to `src/domain/ports/async_unit_of_work_port.py`.
- Updated `tests/fixtures/fakes/fake_subscription_repository.py` so `find_expiring_in_window` is async.
- Added `tests/unit/domain/ports/test_async_repository_contracts.py`.

## Deliberate Boundary

`UnitOfWorkPort` remains as the legacy transition contract. Handler constructor migration and sync UoW deletion are deferred to the request-path, cron, fixture, and final deletion phases because live consumers still exist.

## Verification

- `.venv/bin/pytest tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/app/test_sync_user_with_fake_uow.py tests/unit/app/handlers/test_handler_with_fake_uow.py tests/unit/infra/database/test_uow_async.py -q`
- `.venv/bin/ruff check src/domain/ports/meal_repository_port.py src/domain/ports/user_repository_port.py src/domain/ports/subscription_repository_port.py src/domain/ports/saved_suggestion_repository_port.py src/domain/ports/notification_repository_port.py src/domain/ports/async_unit_of_work_port.py tests/fixtures/fakes/fake_subscription_repository.py tests/unit/domain/ports/test_async_repository_contracts.py`

## Unresolved Questions

None.
