---
phase: 1
title: "Deployment And Regression Gate"
status: in_progress
priority: P1
effort: "1-2d"
dependencies: []
mode: tdd
---

# Phase 1: Deployment And Regression Gate

## Overview

Verify migration deployment state and lock current external behavior before replacing persistence.

## Context Links

- [Plan](./plan.md)
- [Approved design](../reports/brainstorm-260716-1505-four-table-meal-catalog-rework.md)
- Existing recommendation plan: `../260715-1557-catalog-meal-recommendation-mvp/plan.md`

## Requirements

- Confirm whether revisions `20260716000001`-`000003` exist in any shared/staging/production `alembic_version` history.
- Preserve `/v1/meal-recommendations` create/read/swap/log route paths and add skip without changing `/v1/meal-suggestions`.
- Lock owner scoping, idempotent create/log, stale swap rejection, deterministic 9-slot/45-alternative output, feature gating, and `food_reference_id` materialization.

## File Inventory

| Action | Files |
|---|---|
| Modify tests | `tests/unit/api/test_meal_recommendations_route.py`, `tests/unit/app/handlers/test_meal_recommendation_handlers.py` |
| Verify unchanged | `tests/unit/api/test_meal_suggestions_routes.py`, `tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py` |
| Inspect | `migrations/versions/20260716000001_add_catalog_recipe_tables.py`, `20260716000002_add_meal_recommendation_plan_tables.py`, `20260716000003_add_recommendation_swaps_and_interactions.py` |

## Tests Before

1. Add characterization tests for response shape, owner checks, create/log replay, selection version conflicts, and materialized ingredient identity.
2. Record focused baseline commands and results before schema edits.
3. Assert the AI suggestion router and handlers have no recommendation-domain dependency.

## Implementation Steps

1. Record the user's confirmation that the revisions were never deployed, then verify branch ancestry and accessible shared Alembic history before deletion.
2. If any old revision was deployed, stop: preserve history and replace Phases 2-6 with an expand-migrate-contract forward plan.
3. If all are unshipped, record evidence and approve replacing the three revisions with one migration chained from `20260707000001`.
4. Keep `plan_id`/`slot_id` route aliases. If unshipped, intentionally replace response/request fields: remove `catalog_release_id`; rename selected/alternative `recipe_version_id` and request `alternative_recipe_version_id` to `catalog_meal_id`; keep `version` as `selection_version`; add renderable details. Update contract tests together.
5. If any mobile/shared client already consumes the old fields, stop and add a one-release deprecated alias mapper instead of removing them.

## Regression Gate

`.venv/bin/python3.13 -m pytest -q tests/unit/api/test_meal_suggestions_routes.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_recommendations_route.py tests/unit/app/handlers/test_meal_recommendation_handlers.py`

## Success Criteria

- [ ] Deployment status is evidenced, not assumed.
  - Local Alembic head and catalog-table invariants are recorded in `docs/releases/meal-catalog-phase-0-evidence.md`.
  - User confirmed the catalog migration has not deployed to production, so production read-only Alembic checks are not required for the unshipped-migration path.
- [x] Current external behavior has characterization coverage.
  - `tests/migrations/test_catalog_recipe_tables_migration.py` now pins the single catalog migration head and confirms no stored calorie column.
- [x] Migration strategy is explicitly rewrite-unshipped or forward-only.
  - Current source has one head at `20260716000001`; because it is not deployed to production, this phase can continue on the unshipped-migration path.

## Risks And Security

Rewriting deployed history can corrupt schema state. Database evidence is a hard gate. Tests must use owner IDs without logging raw user data.

## Next Steps

Proceed to Phase 2 only after the rewrite-unshipped path is confirmed.
