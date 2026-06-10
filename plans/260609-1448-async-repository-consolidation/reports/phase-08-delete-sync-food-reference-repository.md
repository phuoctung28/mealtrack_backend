# Phase 8 Report: Delete Sync Food Reference Repository

## Summary

- Moved food-reference projection and child-row helper logic into a neutral helper module.
- Rewired `AsyncFoodReferenceRepository` to use the helper module instead of importing the sync repository.
- Deleted sync `FoodReferenceRepository` and its obsolete sync-specific unit test file.
- Preserved nutrient projection coverage in a new helper-focused test.

## Files Changed

- Added: `src/infra/repositories/food_reference_projection.py`
- Modified: `src/infra/repositories/food_reference_repository_async.py`
- Deleted: `src/infra/repositories/food_reference_repository.py`
- Added: `tests/unit/infra/repositories/test_food_reference_projection.py`
- Deleted: `tests/unit/infra/repositories/test_food_reference_repository.py`
- Modified: `tests/architecture/test_async_db_runtime_boundaries.py`

## Verification

- `pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_projection.py tests/unit/infra/repositories/test_food_reference_batch.py tests/unit/infra/repositories/test_food_reference_uow_adapter.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py -q`
  - Result: 28 passed.
- `ruff check src/infra/repositories/food_reference_projection.py src/infra/repositories/food_reference_repository_async.py tests/unit/infra/repositories/test_food_reference_projection.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/architecture/test_async_db_runtime_boundaries.py`
  - Result: all checks passed.

## Boundary

Remaining direct sync DB config/UoW imports are now: `src/infra/database/uow.py` and `src/infra/repositories/notification_repository.py`.

## Unresolved Questions

None.
