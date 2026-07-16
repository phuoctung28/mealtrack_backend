---
title: "Catalog Meal Recommendation MVP"
description: "Build a durable catalog-backed 3-day recommendation flow with canonical ingredients, immutable recipes, deterministic plans, swaps, and normal meal logging."
status: in_progress
priority: P1
branch: "delivery"
effort: "5-7 weeks"
tags: [feature, backend, database, api, recommendation, critical]
blockedBy: []
blocks: []
created: "2026-07-15"
createdBy: "ck:plan"
source: skill
---

# Catalog Meal Recommendation MVP

## Overview

Build a new catalog-specific recommendation bounded context beside the existing AI `/v1/meal-suggestions` flow. PostgreSQL stores immutable recipe versions, 3-day plans, five alternatives per slot, swaps, and raw interactions. Runtime generation and swap use deterministic domain logic only: no LLM, web lookup, Redis dependency, learned popularity, or undo.

Source precedence: the repository-focused foundation report narrows the proposed architecture where they conflict. Therefore `food_reference` remains the only ingredient authority; recipe calories derive from macros; published versions are immutable; learned popularity, Redis recommendation caching, and undo are post-MVP.

## Scope Challenge

- Existing: canonical foods/servings, async UoW, CQRS bus, normal meal persistence, boolean flags, observability.
- Minimum safe change: identity repair -> versioned catalog -> pure ranking -> durable plan API -> swap/logging -> controlled rollout.
- Selected scope: HOLD. Deliver the documented durable MVP; defer ranking sophistication.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Contract And Regression Lock](./phase-01-contract-and-regression-lock.md) | Complete |
| 2 | [Canonical Ingredient And Nutrition Foundation](./phase-02-canonical-ingredient-and-nutrition-foundation.md) | Complete |
| 3 | [Immutable Curated Recipe Catalog](./phase-03-immutable-curated-recipe-catalog.md) | Pending |
| 4 | [Deterministic Recommendation Domain](./phase-04-deterministic-recommendation-domain.md) | Pending |
| 5 | [Durable Plans CQRS And API](./phase-05-durable-plans-cqrs-and-api.md) | Pending |
| 6 | [Transactional Swap And Meal Logging](./phase-06-transactional-swap-and-meal-logging.md) | Pending |
| 7 | [Measurement And Controlled Rollout](./phase-07-measurement-and-controlled-rollout.md) | Pending |

## Dependencies

- No unfinished project plan blocks this work.
- Phase order is sequential. Phase 1 product gates block schema finalization; Phase 2 blocks catalog publication; Phase 3 blocks recommendation and API work.
- Sources: [foundation research](../research/260715-1547-catalog-meal-recommendation-foundation.md), [architecture contract report](../reports/researcher-260715-meal-recommendation-architecture-contract.md), [codebase scout](../reports/scout-260715-meal-recommendation-codebase.md), and `/Users/alexnguyen/Downloads/nutree_meal_recommendation_mvp_architecture.md`.

## MVP Success Criteria

- Complete deterministic 3-day plan: 9 unique slots and 5 valid alternatives per slot.
- Every nutritional recipe ingredient resolves to `food_reference`; calories use backend macro formula.
- Create/swap are owner-scoped, idempotent, durable, and concurrency-safe.
- Recommended recipe logs through the normal meal path without losing `food_reference_id`.
- Default-off rollout is measurable; existing AI suggestions remain unchanged.

## Red Team Review

### Session — 2026-07-15

**Findings:** 15 (14 accepted or accepted with modification, 1 rejected from automatic application)
**Severity:** 2 Critical, 12 High, 1 Medium

- Accepted: catalog acquisition/release trust, nutrition snapshots, verified ingredients, history projection, plan locking, idempotency race/scope/limits, shared meal UoW, handler wiring, production catalog install, analytics privacy, server exposure, and cohort enforcement.
- Allergy finding resolved by user: no filtering/blocking in MVP; disclose `allergy_evaluated: false` and make no safety claim.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all seven phase files.
- Decision deltas checked: canonical ingredients, immutable snapshots, fixed target, raw events, no Redis/popularity/undo, durable plans, catalog-specific names.
- Unresolved contradictions: 0. Validation Session 1 closed the remaining product/data gates.

## Validation Log

### Implementation Slice — 2026-07-16

- **Completed:** Phase 1 regression gate and the first Phase 2 canonical identity repair.
- **Verified:** existing `/v1/meal-suggestions` route behavior remains unchanged; `food_reference_id` now survives request, command, handler materialization, ORM/domain mapping, API response mapping, and normal meal edit reconstruction.
- **Tests:** `.venv/bin/python3.13 -m pytest -q tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/test_meal_edit_database_models.py tests/unit/api/test_meal_mapper.py tests/unit/domain/test_meal_edit_strategies.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py` passed.
- **Lint:** targeted Ruff and `git diff --check` passed.

### Phase 2 Completion — 2026-07-16

- **Completed:** strict catalog ingredient quantity conversion, typed food-reference nutrition projections, and canonical identity preservation across active suggestion, save, cache, mapper, edit, and meal response paths.
- **Verified:** unsafe recipe publication inputs now fail closed: unverified or unapproved foods, missing or implausible macros, ambiguous servings, invalid density, unknown units, invalid quantity, excessive resolved grams, and fiber/sugar values that exceed carbs.
- **Tests:** `.venv/bin/python3.13 -m pytest -q tests/unit/domain/services/meal_recommendation/test_ingredient_quantity_conversion_service.py tests/unit/infra/repositories/test_food_reference_projection.py tests/unit/infra/repositories/test_food_reference_repository_async.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_nutrition.py tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py tests/unit/api/test_meal_suggestion_mapper.py tests/unit/api/test_meal_suggestions_routes.py tests/unit/infra/test_meal_edit_database_models.py tests/unit/api/test_meal_mapper.py tests/unit/domain/test_meal_edit_strategies.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py` passed with 144 tests.
- **Lint:** touched-file Ruff, `.venv/bin/lint-imports`, and `git diff --check` passed.
- **Review:** tester and reviewer agent passes are clean; reviewer-raised fiber plus sugar invariant was fixed and rechecked.

### Session 1 — 2026-07-16

- **Trigger:** `/ck:plan validate`
- **Questions:** 7; all answered. [Full decision record](./reports/validation-260716-catalog-meal-recommendation-decisions.md).
- **Confirmed:** commissioned 180-recipe corpus; disclosure-only allergy scope; supersede-and-retain regeneration; no target override; start today through +7; server-owned events; seed-only publishing; server-side cohort gate.
- **Propagation:** Phases 1, 3, 5, and 7 updated.
- **Whole-plan consistency:** 8 files reread; 7 decision deltas checked; stale references reconciled; 0 unresolved contradictions.
