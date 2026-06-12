# Phase 7 Test Wrapper Removal Slice Report

## Summary

Removed the global generic sync-to-async repository wrapper from test fixtures and added a guard to prevent reintroduction.

## Changes

- `tests/conftest.py`
  - Removed `AsyncSyncRepoWrapper`.
  - Added explicit async test facades for meal and user repository methods used by the legacy sync-session event-bus fixture.
  - Kept `TestUnitOfWork` session ownership behavior unchanged.
- `tests/architecture/test_async_db_runtime_boundaries.py`
  - Added guard against reintroducing the generic wrapper pattern.
- `tests/unit/handlers/command_handlers/test_delete_user_command_handler.py`
  - Replaced local wrapper classes with explicit SQLite-backed async test doubles.
- `src/infra/repositories/base.py`
  - Removed `get_async` and `add_async` compatibility shims.
- `src/infra/repositories/subscription_repository.py`
  - Removed async compatibility shims from the legacy sync repository.
- `tests/unit/infra/repositories/test_base_repository.py`
- `tests/unit/repositories/test_subscription_repository.py`
  - Removed tests that only exercised sync-repository async shims.
- `tests/unit/infra/repositories/test_food_reference_repository.py`
  - Removed sync `SessionLocal` patching from food-reference SQL behavior tests.
  - Kept in-memory business-rule tests and shared mapper projection checks.
- `tests/unit/infra/repositories/test_food_reference_repository_async.py`
  - Added async coverage for normalized-name lookup, atomic upsert, verified-row protection, and empty batch lookup.
- `tests/unit/infra/repositories/test_food_reference_batch.py`
  - Migrated batch lookup tests to `AsyncFoodReferenceRepository` with an async session fake.
- `tests/unit/test_notification_repository.py`
  - Removed dependency on the root `ScopedSession` fixture from the `db=None` session-management test.
  - Patched `NotificationRepository`'s own session factory directly and asserted created-session close behavior.

## Verification

- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py -q`
- `.venv/bin/pytest tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/architecture/test_async_db_runtime_boundaries.py -q`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/domain/ports/test_async_repository_contracts.py -q`
- `.venv/bin/ruff check tests/architecture/test_async_db_runtime_boundaries.py`
- `.venv/bin/ruff check tests/architecture/test_async_db_runtime_boundaries.py src/infra/repositories/base.py tests/unit/infra/repositories/test_base_repository.py`
- `.venv/bin/ruff check --select F821,F822,F823 tests/conftest.py`
- `.venv/bin/python -m py_compile tests/conftest.py`
- `.venv/bin/pytest tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_batch.py tests/architecture/test_async_db_runtime_boundaries.py -q`
- `.venv/bin/ruff check tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_batch.py`
- `.venv/bin/pytest tests/unit/test_notification_repository.py -q`
- `.venv/bin/ruff check tests/unit/test_notification_repository.py`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`232 passed, 3 warnings`)

## Boundary

This is still an in-progress Phase 7 slice. Integration fixtures still contain sync session factories and sync DB patching for legacy tests. The real-Postgres no-op `mock_scoped_session` overrides are intentionally retained until the root autouse fixture is removed or narrowed.

## Unresolved Questions

None.
