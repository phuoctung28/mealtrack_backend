---
phase: 1
title: "Contract And Regression Lock"
status: complete
priority: P1
effort: "2-3d"
dependencies: []
---

# Phase 1: Contract And Regression Lock

## Overview

Lock public/domain contracts and protect existing AI suggestion and meal logging behavior before schema work.

## Context Links

- [Plan](./plan.md)
- [Architecture reconciliation](../reports/researcher-260715-meal-recommendation-architecture-contract.md)
- Existing routes: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meal_suggestions.py`

## Key Insights

- Legacy persistent `meal_plans` tables were dropped; do not revive their generic model names.
- Durable plan and recipe-version requirements are explicit; the scout's response-only option is rejected.
- Validation Session 1 locked regeneration, measurement, allergy, target, start-date, publishing, and rollout contracts.

## Requirements

- Functional: freeze `/v1/meal-recommendations` create/read/swap/log contracts, `allergy_evaluated=false`, error codes, idempotency headers/fields, and catalog-specific names. Allergy profiles are neither filtered nor blocked in MVP.
- Non-functional: old `/v1/meal-suggestions` behavior unchanged; no runtime AI/external lookup in the new path.

## Architecture

Use `CatalogRecipe`/`CatalogRecipeVersion` and `MealRecommendationPlan` naming. Commands own writes; queries own reads; critical records stay in the same UoW transaction.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_meal_suggestions_routes.py` (regression only)
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/test_meal_edit_database_models.py`
- Create later from this contract: request/response schemas listed in Phases 5-6

## Implementation Steps

1. Regeneration creates a new active plan, marks the prior active plan `superseded`, and retains immutable history; no automated deletion in MVP.
2. Disable client target overrides. Accept user-local `start_date` from today through +7 days and snapshot one generation-time backend target for all three dates; do not recompute future weekly-budget targets.
3. Use server-owned `plan_shown`, `alternatives_shown`, `swap_selected`, and `meal_logged` events only.
4. Kill switch blocks create/swap/log writes but permits authenticated owner-scoped reads of already persisted plans.
5. Specify typed failures: feature disabled, invalid start date, catalog insufficient, not found for cross-user access, stale slot version 409, idempotent replay.
6. Add regression tests for existing AI discover/generate/save routes and existing manual meal mapper behavior.
7. Define stable API examples and version names without changing production code yet.

## Todo

- [x] Product decisions recorded and reflected in every later phase.
- [x] Existing suggestion and meal logging regression tests pass.
- [x] No generic `MealPlan` persistence name introduced.

## Success Criteria

- [x] Contract review has zero unresolved schema-blocking questions.
- [x] `.venv/bin/python3.13 -m pytest -q tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/test_meal_edit_database_models.py` passes.

## Implementation Log

### 2026-07-16

- Locked legacy `/v1/meal-suggestions` save/discover/recipe route regressions while preserving the removed `/generate` behavior.
- Added canonical food-reference regression coverage to existing meal mapper and edit tests so schema work starts from a protected baseline.
- Verified with the expanded targeted suite and Ruff; no generic `MealPlan` persistence names were introduced.

## Risk Assessment

Silent contract drift causes migration churn. Mitigation: phase gate; schema work cannot start while decisions remain unresolved.

## Security Considerations

Owner-scoped not-found semantics; allergies ignored for MVP; explicit false evaluation disclosure; no safety claim or raw food/profile payloads in logs/analytics.

## Next Steps

- Proceed to Phase 2; Validation Session 1 approved the contract gate.

## Unresolved Questions

None.
