---
type: brainstorm
date: 2026-07-16
status: amended-and-approved
scope: catalog-meal-recommendation-rework
---

# Four-Table Meal Catalog Rework

## Decision Amendment — 2026-07-16

The user approved a fourth table, `meal_recommendation_operations`, to preserve full historical request replay for swaps and other state-changing recommendation operations. The three catalog migrations on the feature branch have not been deployed and may be replaced directly. All other scope decisions remain unchanged.

## Summary

Replace the current 12-table catalog/recommendation persistence with four new tables. Reuse `food_reference` for ingredient identity and nutrition. Keep `/v1/meal-suggestions` unchanged. Initial learning uses durable recommendation outcomes only; learned ranking waits for enough real usage.

## Confirmed Requirements

- Team supplies an initial 180-meal catalog.
- Import is additive only. Existing catalog rows are never automatically updated or deleted.
- Exact duplicates must not be inserted. Possible near-duplicates must be reported for review.
- No source, rights, release, recipe-version, or separate event tables in this slice.
- Ingredients reference existing `food_reference` rows.
- Recommendation persistence identifies user, recommendation batch, date, meal type, candidates, selected meal, and outcome.
- MVP learning signals: shown, selected/swapped, skipped, and logged.
- Existing AI meal suggestion routes and persistence remain unchanged.

## Evaluated Approaches

### Two Tables

`meal_catalog` plus `meal_recommendations`, with ingredients embedded as JSON.

- Pros: smallest table count.
- Cons: cannot enforce ingredient foreign keys; harder dedup/querying; violates repository 3NF rules.
- Decision: rejected.

### Three Tables

`meal_catalog`, `meal_catalog_ingredients`, and `meal_recommendations`.

- Pros: smallest schema that preserves ingredient foreign keys, candidate rows, additive imports, and outcome learning.
- Cons: no catalog version history or detailed event stream; corrections require an explicit later workflow.
- Decision: approved.

### Six Tables

Retain catalog releases, immutable recipe versions, ingredients, plans, candidates, and events.

- Pros: stronger rollback, audit, and temporal history.
- Cons: unnecessary for a curated 180-meal pilot; higher import and repository complexity.
- Decision: deferred unless pilot requirements expand.

## Approved Data Design

### `meal_catalog`

- Stable UUID primary key and human-controlled unique `catalog_key`.
- Unique `content_hash` derived from canonical cuisine, normalized name, meal eligibility, ordered `food_reference_id` plus resolved grams, and normalized instructions.
- Name, cuisine, description, image, instructions, servings, macro totals, meal-type eligibility booleans, active flag, timestamps.
- Calories are derived from macros and never stored independently.

### `meal_catalog_ingredients`

- Catalog meal foreign key and `food_reference_id` foreign key.
- Quantity, unit, resolved grams, display name, display position.
- No second ingredient nutrition authority. Nutrition resolves from `food_reference`; logged meals receive normal immutable food-item snapshots.
- Unique catalog-meal plus position constraint.

### `meal_recommendations`

- One row per candidate, grouped by `batch_id`, user, recommendation date, and meal type.
- Catalog meal foreign key, candidate rank, selected flag, score, algorithm version, target macros/calories, outcome timestamps, logged meal foreign key, idempotency key, timestamps.
- Candidate rank `0` starts selected; alternatives use ranks `1..N`. Swap changes selection transactionally within the slot.
- Unique batch/date/meal-type/rank and batch/date/meal-type/catalog-meal constraints.
- At most one selected candidate per batch/date/meal type via a partial unique index.

## Import And Duplicate Policy

1. Validate schema, ingredient references, units, resolved grams, macro ranges, meal eligibility, and required fields before writes.
2. Build canonical `content_hash` after ingredient resolution.
3. Reject duplicate `catalog_key` within the file or database.
4. Skip exact existing `content_hash` matches and report them as duplicates.
5. Flag normalized name plus cuisine matches and similar ingredient signatures for manual review; do not auto-merge them.
6. Insert only validated, non-duplicate meals and ingredients in one transaction.
7. Return deterministic imported, skipped-duplicate, rejected, and review-required reports.
8. Re-running the same import produces zero inserts.

## Learning Strategy

- Use recommendation rows as the MVP outcome record.
- Record when candidates are shown, which candidate is selected, whether the slot is skipped, and which selection becomes a logged meal.
- Combine outcomes with existing meal history for later offline analysis.
- Keep deterministic ranking for launch.
- Add learned ranking only after defining a minimum sample size, offline evaluation, and safe fallback to deterministic ranking.

## Rework Boundary

- Remove the three new unshipped migrations and replace them with one timestamped migration because this feature branch has not reached `delivery`.
- Replace catalog release/version repositories with a direct catalog repository.
- Collapse plan/slot/alternative/swap/interaction persistence into one recommendation repository.
- Preserve working CQRS routes, owner checks, idempotency, normal meal materialization, feature gate, and analytics adapter where they still fit.
- Update API responses to include renderable catalog meal details.
- Do not change `/v1/meal-suggestions`, general manual meal creation, parse-text, or unrelated database normalization.

## Success Criteria

- Exactly three feature tables after migration.
- Initial 180 meals import without unresolved ingredients or exact duplicates.
- Same file can be imported repeatedly without new rows.
- Three-day recommendations remain owner-scoped, deterministic, swappable, and loggable.
- Recommendation outcomes are queryable without a separate event store.
- Calories always follow the backend macro formula.
- Existing AI meal suggestion tests remain green.

## Risks

- No immutable recipe history: mitigate with additive-only imports and explicit future correction workflow.
- Near-duplicate false positives: report only; human decides.
- Outcome columns cannot reconstruct every UI event: accepted for MVP.
- Migration rewrite unsafe after production deployment: hard gate requires confirmation that the three current migrations were never deployed outside this feature branch.

## Unresolved Questions

- Confirm deployment state of migrations `20260716000001` through `20260716000003` before implementation. Plan assumes they are unshipped and may be replaced.
