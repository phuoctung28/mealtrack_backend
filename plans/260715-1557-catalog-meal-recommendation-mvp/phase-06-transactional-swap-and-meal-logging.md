---
phase: 6
title: "Transactional Swap And Meal Logging"
status: pending
priority: P1
effort: "5-7d"
dependencies: [5]
---

# Phase 6: Transactional Swap And Meal Logging

## Overview

Replace one slot transactionally and log a selected recipe version through the normal meal flow.

## Context Links

- [Plan](./plan.md)
- Existing meal persistence: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/meal_repository_async.py`

## Key Insights

- Slot row locking, expected version, and request replay are required; other eight slots must not change.
- Logging must snapshot macros and preserve `food_reference_id`; no separate cooked/completed state or undo.

## Requirements

- Functional: swap by request ID + expected slot version; precomputed alternative first, deterministic fallback; log current slot recipe as normal meal once.
- Non-functional: same-transaction audit and raw events; concurrency-safe; no AI/Redis/external calls.

## Architecture

Add `meal_recommendation_swaps` and raw `meal_recommendation_interactions`. Swap command locks the owned parent plan then the slot and returns replayed committed result. Logging materializes immutable version snapshots into ordinary `FoodItem`s.

## Related Code Files

- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/migrations/versions/<timestamp>_add_recommendation_swaps_and_interactions.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/commands/meal_recommendation/swap_meal_recommendation_slot_command.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/commands/meal_recommendation/log_recommended_meal_command.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_recommendation/swap_meal_recommendation_slot_command_handler.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/recommended_meal_materialization_service.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/meal_swap_policy.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/meal_repository_async.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meal_recommendations.py`

## Implementation Steps

1. Add audit/event migration with unique `(slot_id, sequence)`, unique swap request ID, bounded enum, and owner-context FKs.
2. Lock the owned parent plan before the slot, then implement scoped idempotent replay, expected-version conflict, and plan-version increment; test concurrent swaps on different slots as well as the same slot.
3. Revalidate alternative against current plan; consume first valid precomputed row or use deterministic fallback.
4. Persist slot, audit, `swap_selected`, and version changes atomically; return updated slot/day totals.
5. Extract a meal-materialization application service accepting the caller's UoW repositories. Persist duplicate-log claim, ordinary meal, and `meal_logged` atomically; run cache invalidation only after outer commit.
6. Import/register both handlers in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py`; API tests must use `get_configured_event_bus()`.
7. Test injected failure after each write, parallel same/different-slot swaps, stale versions, replay, exhausted alternatives, cross-user access, rollback, and identity preservation.

## Todo

- [ ] Only selected slot changes under all swap tests.
- [ ] Normal meal logging preserves canonical IDs and macro snapshot.
- [ ] No undo or separate completion workflow added.

## Success Criteria

- [ ] Concurrent integration tests prove one winner and deterministic 409/replay behavior.
- [ ] Existing meal queries include logged recommendation exactly once.

## Risk Assessment

Race conditions can overwrite choices or duplicate meals. Mitigation: row locks, versions, unique request keys, and concurrency tests against PostgreSQL.

## Security Considerations

Controlled reason enum; owner-scoped IDs; no free text or recipe content in logs/metrics.

## Next Steps

- Phase 7 exposes bounded measurement and rollout gates.
