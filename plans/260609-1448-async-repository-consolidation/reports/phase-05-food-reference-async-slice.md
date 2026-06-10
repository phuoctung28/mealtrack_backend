# Phase 5 Food Reference Async Slice Report

## Summary

Added an async food reference repository and made nutrition lookup services compatible with async food-reference methods.

## Changes

- `src/infra/repositories/food_reference_repository_async.py`
  - Adds `AsyncFoodReferenceRepository`.
  - Supports barcode/id/FDC lookup, name search, normalized-name batch lookup, single normalized-name lookup, normalized-name upsert, and barcode cache upsert.
  - Uses `AsyncSession` and flush-only writes.
  - Reuses legacy projection/build helpers to preserve response shape.
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
  - Awaits async `find_batch_by_normalized_names` and `find_by_normalized_name` when provided.
  - Keeps `to_thread` fallback for legacy sync repositories.
- `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`
  - Awaits async `upsert_by_normalized_name` when provided.
  - Keeps `to_thread` fallback for legacy sync repositories.
- `src/infra/database/uow_async.py`
  - Exposes `food_references`.
- `src/domain/ports/async_unit_of_work_port.py`
  - Declares `food_references`.
- `src/infra/repositories/food_reference_uow_adapter.py`
  - Provides singleton-safe async food-reference methods using fresh `AsyncUnitOfWork` scopes.
- `src/api/base_dependencies.py`
  - Uses the async adapter for nutrition lookup and ingredient resolver singletons.

## Verification

- `.venv/bin/pytest tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/database/test_uow_async.py -q`
- `.venv/bin/ruff check src/infra/repositories/food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py`
- `.venv/bin/ruff check --select F,I src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py src/domain/services/meal_suggestion/nutrition_lookup_service.py src/infra/database/uow_async.py src/domain/ports/async_unit_of_work_port.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/database/test_uow_async.py`
- `.venv/bin/pytest tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/api/test_event_bus_dependency_singletons.py -q`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`232 passed, 3 warnings`)
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py -q` (`47 passed`)
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/dependencies/test_meal_image_cache.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/repositories/test_pgvector_meal_image_cache_repository_async.py tests/unit/infra/repositories/test_pending_meal_image_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_repository.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/repositories/test_meal_translation_repository_async.py tests/unit/infra/repositories/test_base_repository.py tests/unit/repositories/test_subscription_repository.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py tests/unit/api/test_feature_flags_routes.py tests/unit/domain/ports/test_async_repository_contracts.py tests/unit/infra/repositories/test_subscription_repository_async.py tests/unit/infra/database/test_uow_async.py tests/unit/cron/test_push_cron.py tests/unit/cron/test_email_cron.py tests/unit/infra/services/test_cron_trial_push_service.py tests/unit/infra/test_cron_notification_dispatch_service.py tests/unit/infra/services/test_cron_lifecycle_email_service.py tests/unit/handlers/command_handlers/test_user_command_handlers.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py tests/unit/handlers/command_handlers/test_delete_user_command_handler.py tests/unit/test_notification_repository.py -q` (`237 passed, 3 warnings`)

## Boundary

The singleton `get_food_reference_repository()` still exists as a backward-compatible factory, but production barcode and nutrition suggestion flows now use async UoW-backed food-reference access.

## Unresolved Questions

None.
