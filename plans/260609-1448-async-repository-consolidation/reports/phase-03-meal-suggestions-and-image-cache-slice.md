# Phase 3 Meal Suggestions and Image Cache Slice Report

## Summary

Migrated meal suggestion image-cache request-path dependencies to async DB access and pulled forward the pgvector/pending queue async repository slice needed to avoid sync request work.

## Changes

- `src/api/dependencies/meal_image_cache.py`
  - Uses `get_async_db`.
  - Builds async pgvector and pending queue repositories.
- `src/api/routes/v1/meal_suggestions.py`
  - Uses `AsyncSession`.
  - Commits after enqueueing pending image misses.
- `src/infra/repositories/pgvector_meal_image_cache_repository_async.py`
  - Adds async pgvector cache repository.
  - Rolls back failed batch cache queries for transaction recovery.
  - Flushes upserts without committing internally.
- `src/infra/repositories/pending_meal_image_repository_async.py`
  - Adds async pending queue repository.
  - Flushes queue writes without committing internally.
- `src/api/base_dependencies.py`
  - Replaced sync `SessionLocal` profile lookup with async `AsyncUnitOfWork`.
  - Removed unused `get_meal_repository` sync dependency.
- `src/domain/services/meal_suggestion/suggestion_orchestration_service.py`
  - Accepts async profile providers while preserving sync test providers.
- `src/app/handlers/query_handlers/lookup_barcode_query_handler.py`
  - Uses async UoW scopes for production local-cache reads and cache writes.
  - Retains legacy repository fallback for focused tests and transitional callers.
- `src/api/dependencies/event_bus.py`
  - Wires `LookupBarcodeQueryHandler` with `AsyncUnitOfWork` instead of the sync food-reference singleton.
- `tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py`
  - Covers async UoW cache hit and FatSecret cache-write paths.
- `src/infra/repositories/food_reference_uow_adapter.py`
  - Adds singleton-safe async food-reference access through fresh UoW scopes.
- `src/api/base_dependencies.py`
  - Wires nutrition lookup and ingredient resolver singletons to the async adapter.
- `tests/architecture/test_async_db_runtime_boundaries.py`
  - Adds a guard preventing request-path food-reference services from wiring the sync singleton.
- `src/infra/repositories/meal_translation_uow_adapter.py`
  - Adds singleton-safe async meal-translation access through fresh UoW scopes.
- `src/api/base_dependencies.py`
  - Wires DeepL meal translation to the async adapter.

## Verification

- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py -q`
- `.venv/bin/pytest tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py -q`
- `.venv/bin/ruff check tests/architecture/test_async_db_runtime_boundaries.py src/api/dependencies/meal_image_cache.py src/api/routes/v1/meal_suggestions.py src/infra/repositories/pgvector_meal_image_cache_repository_async.py src/infra/repositories/pending_meal_image_repository_async.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py`
- `.venv/bin/ruff check --select F,I src/api/base_dependencies.py src/domain/services/meal_suggestion/suggestion_orchestration_service.py tests/unit/domain/services/test_suggestion_orchestration_service.py`
- `.venv/bin/pytest tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/api/test_event_bus_dependency_singletons.py -q`
- `.venv/bin/ruff check src/app/handlers/query_handlers/lookup_barcode_query_handler.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py src/infra/repositories/food_reference_repository_async.py`
- `.venv/bin/ruff check --select F821,F822,F823 src/api/dependencies/event_bus.py`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`232 passed, 3 warnings`)
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py -q` (`47 passed`)
- `.venv/bin/ruff check tests/architecture/test_async_db_runtime_boundaries.py src/infra/repositories/food_reference_uow_adapter.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py`
- `.venv/bin/ruff check --select F821,F822,F823,I src/api/base_dependencies.py`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`237 passed, 3 warnings`)
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/repositories/test_meal_translation_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/infra/repositories/test_meal_translation_repository_async.py -q` (`22 passed`)
- `.venv/bin/ruff check tests/architecture/test_async_db_runtime_boundaries.py src/infra/repositories/meal_translation_uow_adapter.py tests/unit/infra/repositories/test_meal_translation_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/infra/repositories/test_meal_translation_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`241 passed, 3 warnings`)

## Remaining Work

- Convert remaining request-path sync repository consumers.
- Migrate scripts and integration fixtures off sync pgvector/pending repositories.
- Remove legacy `get_db` after tests no longer import it.

## Unresolved Questions

None.
