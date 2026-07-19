---
phase: 4
title: "Deterministic Recommendation Domain"
status: complete
priority: P1
effort: "5-7d"
dependencies: [3]
---

# Phase 4: Deterministic Recommendation Domain

## Overview

Implement pure deterministic scoring, nine-slot optimization, and five alternatives per slot.

## Context Links

- [Plan](./plan.md)
- Architecture source sections 8-13 and 25: `/Users/alexnguyen/Downloads/nutree_meal_recommendation_mvp_architecture.md`

## Key Insights

- Cold start uses curated quality, calorie fit, and diversity; learned popularity/exploration is deferred.
- Existing meals with no preserved canonical IDs are cold start; no fuzzy historical backfill is allowed in MVP.
- Existing name search lacks stable ordering; candidate queries require explicit ordering and immutable version snapshots.

## Requirements

- Functional: 3 dates x breakfast/lunch/dinner; unique current recipes; supported cuisines; 5 alternatives/slot; 90-day linked-ingredient affinity.
- Non-functional: same inputs + algorithm version produce same output; domain has no DB/API/AI/Redis imports.

## Architecture

Pure services: calorie allocation, history profile, recipe scoring, three-day optimizer, alternative selection. Candidate retrieval returns ordered immutable projections. Use stable tie-break `(score desc, recipe_version_id asc)`.

## Related Code Files

- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/calorie_allocation_policy.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/ingredient_affinity_service.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/recipe_scoring_service.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/slot_alternative_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/catalog_recipe_repository_async.py`

## Implementation Steps

1. Add table-driven tests for calorie allocation, affinity recency/confidence, score bounds, and stable ties.
2. Query three ordered candidate pools with publication, cuisine, meal-type, nutrition, and tolerance filters.
   Build affinity from a dedicated owner-scoped 90-day linked-ingredient projection ordered newest-first with explicit volume semantics; test histories above 500 meals.
3. Implement ±20%, ±30%, then distance-ranked fallback; typed insufficiency if <9 unique candidates.
4. Optimize daily triplets with diversity/calorie penalties; validate aggregate invariants before persistence.
5. Generate five unique alternatives per slot from the same catalog snapshot; alternatives are not exposures until returned.
6. Add golden/property tests for cold, linked-history, pantry-only, sparse, and repeat-call cases.

## Todo

- [x] Pure service tests written before implementation.
- [x] Stable results and all hard constraints proven.
- [x] Learned popularity and Redis absent.

## Success Criteria

- [x] Every golden case yields 9 valid slots and 45 alternatives or typed insufficiency.
- [x] `.venv/bin/python3.13 -m pytest -q tests/unit/domain/services/meal_recommendation/` passes.

## Implementation Log

### 2026-07-16

- Added deterministic calorie allocation, linked-ingredient affinity, recipe scoring, slot alternatives, and three-day optimizer services.
- Added typed recommendation plan, slot, alternative, and insufficiency domain projections.
- Enforced deterministic sorting by score descending and recipe-version ID ascending; repository active-version ordering now uses version ID.
- Added golden tests for calorie allocation, 90-day affinity, stable ties, sparse catalog insufficiency, repeat-call determinism, and 9-slot/45-alternative plan invariants.
- Verified Phase 4 suite, Ruff, targeted mypy, and import-linter.

## Risk Assessment

Greedy selection can dead-end. Mitigation: bounded daily-triplet search plus shallow backtracking and final invariant validation.

## Security Considerations

History input is owner-scoped and reduced to canonical IDs/weights; never log ingredients or profile content.

## Next Steps

- Phase 5 orchestrates this domain service transactionally.
