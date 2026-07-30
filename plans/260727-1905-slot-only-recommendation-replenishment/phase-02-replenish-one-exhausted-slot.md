---
phase: 2
title: "Replenish One Exhausted Slot"
status: in-progress
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 2: Replenish One Exhausted Slot

## Overview

Preserve normal swaps, but when no unseen active alternative remains, generate and persist a new five-alternative pool for the requested slot only.

## Related Code Files

- Modify: `src/app/handlers/command_handlers/meal_recommendation/swap_meal_recommendation_slot_command_handler.py`
- Modify: `src/domain/ports/meal_recommendation_plan_repository_port.py`
- Modify: `src/infra/repositories/meal_recommendation_plan_repository_async.py`
- Modify: `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- Modify: `src/api/dependencies/event_bus.py`
- Extend: `tests/unit/app/handlers/test_meal_recommendation_handlers.py`
- Extend: `tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py`
- Create: `tests/integration/postgres/test_meal_recommendation_slot_concurrency.py`

## Architecture

`swap` first locks and validates only the requested slot. It selects the next unseen active alternative. If none exists, it derives a new alternative pool using the existing catalog snapshot, calorie target, user affinity, and exclusions: all candidates ever seen in this slot plus all currently selected meals in other slots. It then rechecks the target slot version under lock, retires only its old inactive candidates, persists five new inactive alternatives, selects the first fresh one, and records the normal idempotent swap operation.

## Tests Before

1. Five automatic swaps traverse the five initially stored alternatives without repetition; the sixth swap replenishes only that slot and selects one fresh alternative.
2. Explicit user selection still accepts only an active unseen alternative.
3. Stale version, logged, skipped, invalid target, and idempotent replay semantics remain unchanged.
4. Two concurrent exhausted-pool swaps yield one replacement pool and one selected candidate.
5. Replenishment excludes selected meals in all other slots and every seen meal in the target slot.
6. SQL characterization proves no full-batch hydration and locks no unrelated slot.

## Implementation Steps

1. Extract the existing alternative-ranking seam needed to score one slot without rebuilding a full plan.
2. Add repository operations for active pool/seen IDs, other selected IDs, and atomic retirement/insertion for one slot.
3. Update swap handler orchestration without holding an open transaction across unrelated network/AI work; catalog ranking remains deterministic and local. Re-lock and recheck candidate exhaustion before writing.
4. Enforce per-slot candidate identity uniqueness at persistence level or handle the database conflict deterministically, so concurrent replenishment cannot insert duplicate candidates.
5. Preserve the current endpoint and `MealRecommendationSlotDetailResponse`; return the refreshed slot only.
6. Add distinct operation outcome/latency dimensions for `stored_candidate` and `replenished_candidate` without user IDs or meal names.

## Success Criteria

- [x] Repository mutation returns a complete changed-slot result and stable plan ID.
- [x] Duplicate request IDs are rechecked after the slot lock.
- [ ] PostgreSQL concurrency proves one replacement pool and unrelated-slot immutability.
- [ ] Repeated HTTP automatic swaps prove no seen-candidate cycling.

## Risks

Ranking while retaining a row lock could worsen the known small-pool incident. Keep lock windows restricted to validation and persistence; revalidate state before writing replacement candidates.
