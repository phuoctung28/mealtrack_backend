---
phase: 4
title: "Aggregate Affinity And Fast Generation"
status: completed
priority: P1
effort: "2d"
dependencies: [1, 3]
mode: tdd
---

# Phase 4: Aggregate Affinity And Fast Generation

## Overview

Replace hydration of up to 5,000 historical meals and food-item objects with one owner-scoped aggregate query while preserving affinity semantics.

## Requirements

- Query only canonical `food_reference_id`, local age-day bucket, and capped effective quantity for the prior 90 days.
- Preserve owner/status filters, `coalesce(ready_at, created_at)`, timezone boundaries, unlinked exclusion, per-item 500 g cap, recency decay, and confidence.
- SQL aggregates evidence; `IngredientAffinityService` continues to own scoring policy.
- Do not add indexes until representative `EXPLAIN ANALYZE` proves one is missing.

## File Inventory

| Action | Files |
|---|---|
| Modify | `src/domain/ports/meal_repository_port.py` |
| Modify | `src/infra/repositories/meal_repository_async.py` |
| Modify | `src/app/services/meal_recommendation_history_projector.py` |
| Modify | `src/domain/services/meal_recommendation/ingredient_affinity_service.py` |
| Modify | create recommendation handler stage instrumentation |
| Extend | `tests/unit/app/services/test_meal_recommendation_history_projector.py`, `tests/integration/infra/repositories/test_meal_repository_async.py` |
| Add | `tests/unit/infra/repositories/test_meal_repository_history_aggregate.py` |
| Conditional | one timestamped Alembic index migration only with query-plan evidence |

## Function And Interface Checklist

- Add immutable `IngredientHistoryBucket(food_reference_id, age_days, capped_grams)`.
- Add `MealRepositoryPort.aggregate_linked_ingredient_history(...)`.
- Change `MealRecommendationHistoryProjector.build_affinity(...)` to buckets and remove `find_by_date_range(... limit=5000)`.
- Keep affinity service pure/deterministic.

## Tests Before

1. Bucket output produces the same profile as the phase-1 event characterization.
2. Cover UTC/non-UTC boundaries, `ready_at` fallback, empty/unlinked history, deleted/inactive meals, per-item cap before bucket aggregation, and owner isolation.
3. Assert query projection never hydrates Meal/Nutrition/FoodItem trees.
4. Record representative 90-day `EXPLAIN ANALYZE`.
5. Handler proves warm create uses one affinity query and zero date-range calls.

## Refactor

1. Define the bucket at the domain boundary.
2. Implement grouped SQL with timezone-safe age buckets and cap before `SUM`.
3. Adapt projector without changing current `now` semantics.
4. Remove obsolete `_HISTORY_LIMIT`.
5. Add a concurrent index only with before/after evidence and rollback SQL.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/app/services/test_meal_recommendation_history_projector.py tests/unit/infra/repositories/test_meal_repository_history_aggregate.py tests/integration/infra/repositories/test_meal_repository_async.py tests/unit/app/handlers/test_meal_recommendation_handlers.py
```

## Success Criteria

- [x] Generation performs one bounded aggregate query and hydrates no historical meal graph.
- [x] Affinity matches phase-1 characterization at timezone/recency boundaries.
- [ ] Warm generation meets <500 ms staging p95 with zero full-catalog SQL.
- [x] Any index has before/after query-plan evidence.

## Completion Evidence

- Added `IngredientHistoryBucket` and bucket-based affinity projection.
- Added `aggregate_linked_ingredient_history(...)` to the meal repository port and async repository.
- Updated recommendation history projector to use the aggregate method instead of `find_by_date_range`.
- Local deterministic and synthetic benchmark gates passed; staging p95 evidence still needs a pinned/staging runner.
- No index migration was added because no representative staging query-plan evidence showed one was needed.

## Risks And Security

Owner filtering happens inside SQL. Never emit user food IDs in metrics or benchmark artifacts.

## Next Steps

Optimize swap/log so mutations do not undo generation/read gains.
