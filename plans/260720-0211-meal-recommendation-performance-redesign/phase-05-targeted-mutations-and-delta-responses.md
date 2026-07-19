---
phase: 5
title: "Targeted Mutations And Delta Responses"
status: completed
priority: P1
effort: "2-3d"
dependencies: [1, 2]
mode: tdd
---

# Phase 5: Targeted Mutations And Delta Responses

## Overview

Lock, hydrate, mutate, and return only the requested slot for swap/log while retaining operation replay.

## Requirements

- SQL includes owner-anchor authorization, `batch_id`, and `slot_id`, locking at most that slot's six candidates.
- Preserve optimistic versioning, historical replay, fingerprint conflicts, duplicate-log prevention, and same-UoW state changes.
- Swap/log return plan ID and one fully hydrated changed slot; they never reload the full plan.
- Pass the already-loaded selected catalog meal to materialization; remove the fake one-byte image and allow `Meal.image=None`.

## File Inventory

| Action | Files |
|---|---|
| Modify | recommendation domain model for a typed slot mutation result |
| Modify | `src/domain/ports/meal_recommendation_plan_repository_port.py` |
| Modify | `src/infra/repositories/meal_recommendation_plan_repository_async.py` |
| Modify | swap/log handlers and `recommended_meal_materialization_service.py` |
| Modify | recommendation route/support serializers |
| Extend | plan-repository, handler, materialization, and route tests |
| Add | `tests/integration/infra/repositories/test_meal_recommendation_slot_concurrency.py` |

## Function And Interface Checklist

- Add `MealRecommendationSlotMutationResult` with plan/slot IDs, selected meal, version, logged meal ID, and target-slot alternatives.
- Replace full-batch mutation loaders with owner-scoped `_load_slot_for_update(...)`.
- Operation replay returns the same stored delta as the first request.
- Materializer accepts the selected catalog projection and makes no catalog lookup.
- `to_slot_mutation_response(...)` serializes one slot and is the only mutation response.

## Tests Before

1. SQL/integration tests prove owner anchor, batch/slot predicates, `FOR UPDATE`, and <=6 rows.
2. Same request replays same delta; different fingerprint conflicts; stale/logged conflicts remain.
3. Concurrent swaps leave one selected; competing logs create one normal meal; unrelated slots are not locked.
4. Warm delta mutation performs replay lookup plus one slot lock and no batch reload.
5. Materialization uses supplied meal, backend calorie logic, and no fake image.
6. HTTP/OpenAPI contract contains one changed slot and no full-plan mutation response.

## Refactor

1. Separate slot mutation projection from full-plan projection.
2. Authorize through an owner-scoped anchor subquery before locking.
3. Persist sufficient operation result data for equivalent replay using the existing four tables.
4. Return typed mutation results directly from the route.
5. Remove placeholder image persistence.

## Tests After And Regression Gate

```bash
.venv/bin/python3 -m pytest -q tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/app/handlers/test_meal_recommendation_handlers.py tests/unit/app/services/test_recommended_meal_materialization_service.py tests/unit/api/test_meal_recommendations_route.py tests/integration/infra/repositories/test_meal_recommendation_slot_concurrency.py
```

## Success Criteria

- [x] Swap/log lock and hydrate one owner-scoped slot only.
- [x] Delta responses never reload or serialize the other eight slots.
- [x] Swap/log expose only the changed-slot contract.
- [x] Log creates one normal meal with no fabricated image.
- [ ] Swap/log delta meet <300 ms staging p95.

## Completion Evidence

- Added typed slot mutation results and changed swap/log routes to return one slot detail response.
- Added owner-anchored slot lock path for swap/log instead of full-batch mutation hydration.
- Updated materialization to use the selected hydrated catalog projection and keep `Meal.image` unset.
- Focused route, handler, repository, and materialization tests pass.
- Staging p95 remains a rollout gate for Phase 7.

## Risks And Security

Never trust `plan_id` alone. Prove locks on PostgreSQL; compiled-SQL tests cannot prove concurrency.

## Next Steps

Update Flutter against this final changed-slot contract.
