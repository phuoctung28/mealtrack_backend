---
phase: 2
title: "Four-Table Schema And Model Collapse"
status: complete
priority: P1
effort: "2-3d"
dependencies: [1]
mode: tdd
---

# Phase 2: Four-Table Schema And Model Collapse

## Overview

Replace the 12-table ORM/migration shape with exactly four focused tables and direct domain projections.

## Requirements

- `meal_catalog`: UUID, unique `catalog_key`, unique SHA-256 `content_hash`, typed eligibility flags, instructions snapshot, macro totals, no calories column.
- `meal_catalog_ingredients`: catalog and `food_reference` FKs, quantity/unit/resolved grams/position.
- `meal_recommendations`: self-referenced candidate rows grouped by batch/date/type. One anchor candidate owns batch metadata; other candidates reference it.
- `meal_recommendation_operations`: append-only request replay rows for swap, skip, and log operations.
- Partial unique index guarantees one selected candidate per logical slot.

## Architecture

Candidate rank 0 begins selected; ranks 1-5 are alternatives. The anchor row has `id = batch_id`; all other rows carry a deferrable self-FK to it. Instructions are an immutable render snapshot; eligibility uses booleans. Operations are append-only idempotency/audit facts, not a second learning store.

### Exact Recommendation Columns

| Scope | Columns |
|---|---|
| Every candidate | `id`, `batch_id`, `slot_id`, `recommendation_date`, `meal_type`, `catalog_meal_id`, `candidate_rank`, `is_selected`, `score`, `selection_version`, outcome timestamps, `logged_meal_id`, timestamps |
| Anchor only | `user_id`, `status`, `timezone`, `start_date`, target macros, `algorithm_version`, `operation`, create `idempotency_key`, `request_fingerprint`, `superseded_at` |
| Relationships | anchor `user_id -> users.id CASCADE`; `batch_id -> meal_recommendations.id CASCADE DEFERRABLE`; catalog `RESTRICT`; logged meal `SET NULL` |

`meal_recommendation_operations` columns: UUID ID, `user_id`, `batch_id`, `slot_id`, operation type, request ID, request fingerprint, expected/result selection versions, requested/from/to catalog meal IDs, result logged meal ID, result status, created timestamp. FKs use owner/batch cascade, catalog restrict, and logged meal set-null. Unique `(user_id, operation_type, request_id)` guarantees replay lookup; checks require operation-specific fields and immutable rows.

Checks require anchor metadata only when `id=batch_id`, non-anchor metadata null, nonnegative ranks/targets/scores, valid meal type, coherent logged timestamp/ID, and terminal skip/log exclusivity. Unique constraints cover `(batch_id, slot_id, candidate_rank)` and `(batch_id, slot_id, catalog_meal_id)`; partial unique indexes cover one selected candidate per slot, one active anchor per user, create idempotency on anchors, and non-null logged meal IDs. A trigger verifies every row's logical slot metadata and owner agree with its anchor.

## File Inventory

| Action | Files |
|---|---|
| Replace | `migrations/versions/20260716000001_add_catalog_recipe_tables.py` |
| Delete after safe rewrite | `migrations/versions/20260716000002_add_meal_recommendation_plan_tables.py`, `20260716000003_add_recommendation_swaps_and_interactions.py` |
| Rewrite | `src/infra/database/models/meal_recommendation/catalog_recipe.py`, `meal_recommendation_plan.py` |
| Modify | `src/infra/database/models/meal_recommendation/__init__.py`, `src/infra/database/models/__init__.py` |
| Rewrite tests | `tests/migrations/test_catalog_recipe_tables_migration.py` |

## Tests Before

1. Assert exact four table names, all FKs/checks/unique constraints, selected partial index, operation replay uniqueness, and absence of catalog calories.
2. Add migration/ORM parity and delete-behavior tests.
3. Add base-to-head, downgrade/upgrade, and single-head assertions.

## Refactor

1. Replace catalog release/version/source/right models with `MealCatalogORM` and `MealCatalogIngredientORM`.
2. Replace plan/slot/alternative models with `MealRecommendationORM` candidate rows and replace swap/interaction models with one append-only `MealRecommendationOperationORM`.
3. Use `Numeric`/`Decimal` for hash-sensitive grams/macros.
4. Add `users.id` cascade FK and nullable `meal.meal_id` set-null FK.
5. Implement self-FK anchor checks/trigger and document this four-table aggregate representation in migration/model notes.
6. Register models centrally; keep migration and ORM definitions identical.

## Tests After And Regression Gate

`.venv/bin/python3.13 -m pytest -q tests/migrations/test_alembic_revision_graph.py tests/migrations/test_catalog_recipe_tables_migration.py tests/unit/infra/database/test_uow_async.py`

## Success Criteria

- [ ] Alembic and ORM expose exactly four feature tables.
- [ ] Calories cannot drift because they are not stored.
- [ ] Ownership, selection, idempotency, and FK invariants are database-enforced.

## Risks And Security

The self-referenced anchor avoids batch metadata duplication. Operation rows add only durable replay facts required by the public mutation contract. Owner FKs and owner/batch indexes are mandatory.

## Next Steps

Build direct catalog persistence and import against this schema.
