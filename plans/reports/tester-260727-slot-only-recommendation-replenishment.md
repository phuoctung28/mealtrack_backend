# Slot-Only Recommendation Replenishment Validation

Work context: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend`
Plans: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260727-1905-slot-only-recommendation-replenishment/`

## Diff Scope

Changed files:
- `src/api/dependencies/event_bus.py`
- `src/api/routes/v1/meal_recommendation_route_support.py`
- `src/api/routes/v1/meal_recommendations.py`
- `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py`
- `src/app/handlers/command_handlers/meal_recommendation/swap_meal_recommendation_slot_command_handler.py`
- `src/domain/model/meal_recommendation/meal_recommendation_plan.py`
- `src/domain/ports/meal_recommendation_plan_repository_port.py`
- `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- `src/infra/database/models/meal_recommendation/meal_recommendation_plan.py`
- `src/infra/repositories/meal_recommendation_plan_repository_async.py`
- `tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py`
- plus docs and one Alembic migration

## Commands

1. `pytest tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/api/test_meal_recommendations_route.py tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py`
   - Failed in shell Python 3.10 env:
   - `ImportError: cannot import name 'UTC' from 'datetime'`

2. `.venv/bin/pytest tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/api/test_meal_recommendations_route.py tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py`
   - `49 passed in 1.23s`

3. `.venv/bin/alembic heads`
   - Output: `20260727000001 (head)`

4. `.venv/bin/pytest tests/migrations/test_alembic_revision_graph.py tests/migrations/test_catalog_recipe_tables_migration.py`
   - `10 passed, 1 failed`
   - Failed test: `tests/migrations/test_catalog_recipe_tables_migration.py::test_catalog_schema_has_one_head_and_no_stored_calories`
   - Assertion: expected `['20260726000001']`, got `['20260727000001']`

5. `.venv/bin/pytest tests/unit`
   - `2013 passed, 14 warnings in 92.91s`

6. `.venv/bin/pytest tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/api/test_meal_recommendations_route.py tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py --cov=src --cov-report=term-missing`
   - `49 passed in 3.73s`
   - Coverage: `TOTAL 29.83%`
   - Changed-area coverage highlights:
     - `src/api/routes/v1/meal_recommendation_route_support.py` `93.67%`
     - `src/api/routes/v1/meal_recommendations.py` `83.72%`
     - `src/infra/repositories/meal_recommendation_plan_repository_async.py` `63.04%`

## Findings

- Local recommendation-focused tests passed on the project venv.
- Full unit suite passed.
- Migration graph is a single head, but one migration test is stale against the new head revision.

## Pre-Existing / Non-Code Issues

- Shell `pytest` used Python 3.10 and failed on `datetime.UTC`; project venv `.venv/bin/pytest` is required here.
- Migration expectation in `tests/migrations/test_catalog_recipe_tables_migration.py::test_catalog_schema_has_one_head_and_no_stored_calories` still expects the previous head `20260726000001`.

## Coverage / Gaps

- No direct unit test exercised the new handler replenishment branch; repository replenishment behavior is covered, but the handler branch still needs explicit coverage.
- Migration test should be updated to accept the new head revision.
