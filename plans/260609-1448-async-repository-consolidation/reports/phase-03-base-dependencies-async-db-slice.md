# Phase 3 Report: Base Dependencies Async DB Slice

## Summary

- Kept the public `get_db` dependency symbol for compatibility.
- Changed `get_db` to delegate to `get_async_db`.
- Removed `src/api/base_dependencies.py` from the sync DB import transition allowlist.
- Changed legacy food-reference getter aliases to return the async UoW adapter.

## Files Changed

- `src/api/base_dependencies.py`
- `tests/unit/api/test_food_reference_dependency_wiring.py`
- `tests/architecture/test_async_db_runtime_boundaries.py`

## Verification

- `pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/api/test_food_reference_dependency_wiring.py tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/domain/services/meal_suggestion/test_ingredient_nutrition_resolver.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/domain/services/test_deepl_meal_translation_service.py -q`
  - Result: 57 passed.
- `ruff check src/api/base_dependencies.py src/api/main.py tests/unit/api/test_api_main_firebase_and_lifespan.py tests/architecture/test_async_db_runtime_boundaries.py`
  - Result: all checks passed.
- `pytest tests/unit/api/test_food_reference_dependency_wiring.py tests/architecture/test_async_db_runtime_boundaries.py -q`
  - Result: 11 passed.
- `ruff check src/api/base_dependencies.py tests/unit/api/test_food_reference_dependency_wiring.py tests/architecture/test_async_db_runtime_boundaries.py`
  - Result: all checks passed.

## Boundary

Direct sync DB config/UoW imports are now limited to legacy infra files: `src/infra/database/uow.py`, `src/infra/repositories/food_reference_repository.py`, `src/infra/repositories/meal_translation_repository.py`, and `src/infra/repositories/notification_repository.py`. API wiring no longer lazy-imports the sync food-reference repository.

## Unresolved Questions

None.
