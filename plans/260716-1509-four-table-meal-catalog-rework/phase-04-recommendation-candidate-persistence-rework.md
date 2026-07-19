---
phase: 4
title: "Recommendation Candidate Persistence Rework"
status: in_progress
priority: P1
effort: "3-4d"
dependencies: [3]
mode: tdd
---

# Phase 4: Recommendation Candidate Persistence Rework

## Overview

Collapse plan, slot, alternative, swap, and interaction repositories into candidate-row persistence while preserving deterministic behavior and concurrency guarantees.

## Requirements

- Create persists 54 candidate rows for three days, three meal types, one selected plus five alternatives.
- Direct catalog projections replace active release/version lookups.
- Preserve advisory generation lock, one active/recent batch, create fingerprint replay, owner-scoped reads, optimistic swap, and log claim/finalization.
- Coarse state intentionally stores the latest selection, not full swap history.
- Persist every swap request/result in `meal_recommendation_operations`. Any historical retry replays after fingerprint validation; reused request IDs with different payloads return `409`.

## File Inventory

| Action | Files |
|---|---|
| Rewrite | `src/domain/model/meal_recommendation/catalog_recipe.py`, `meal_recommendation_plan.py` |
| Rewrite | `src/domain/ports/meal_recommendation_plan_repository_port.py`, `src/infra/repositories/meal_recommendation_plan_repository_async.py` |
| Modify | `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py`, `swap_meal_recommendation_slot_command_handler.py`, `log_recommended_meal_command_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_meal_recommendation_plan_query_handler.py`, command/query package exports |
| Retain/adapt | `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`, scoring/allocation/affinity services |
| Rewrite tests | `tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py`, `tests/unit/app/handlers/test_meal_recommendation_handlers.py` |

## Tests Before

1. Lock deterministic 9 selected/45 alternatives and sparse-catalog failure.
2. Lock create replay/fingerprint mismatch, owner scope, generation serialization, stale swap, invalid target, and duplicate logging.
3. Add database concurrency test for one selected candidate after competing swaps.

## Refactor

1. Rename internal identities to batch/logical slot/catalog meal while retaining API aliases.
2. Assemble the plan projection from anchor plus candidate rows ordered by date/type/rank.
3. Persist batch metadata on the anchor only; candidate rows reference it by self-FK.
4. Swap candidates `FOR UPDATE`, verify `selection_version`, clear/select atomically, update coarse timestamps.
5. Claim and finalize logging idempotently in the same UoW as normal meal save.
6. Write operation rows in the same UoW as state changes. On retry, load by owner/type/request ID, compare fingerprint and original context, then replay the stored result.
7. Remove catalog release IDs and the separate swap/interaction tables.

## Tests After And Regression Gate

`.venv/bin/python3.13 -m pytest -q tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py tests/unit/infra/repositories/test_meal_recommendation_plan_repository_async.py tests/unit/app/handlers/test_meal_recommendation_handlers.py`

## Success Criteria

- [ ] Candidate rows reproduce the current plan contract deterministically.
- [ ] Concurrent swaps cannot select two meals.
- [ ] Create and log retries cannot duplicate state or meals.
- [ ] Any historical swap retry replays; payload-mismatched request IDs conflict deterministically.
- [ ] No release/version/plan/slot/event repository dependency remains.

## Risks And Security

Candidate-row fanout is bounded. Owner is verified through the anchor row before candidate read/update; indexes follow owner/batch/date access paths.

## Next Steps

Adapt API rendering, explicit skip, materialization, and analytics.
