---
title: Catalog Meal Recommendation and Ingredient Foundation
type: research
status: draft
created: 2026-07-15
scope: high-level
---

# Research Report: Catalog Meal Recommendation and Ingredient Foundation

## Executive Summary

Build the new recommendation feature on a curated, versioned recipe catalog backed by the existing `food_reference` ingredient base. Do not create a second ingredient authority. A recipe ingredient should reference a canonical food, store its recipe quantity and unit, and resolve that quantity to grams for nutrition calculation.

The first deliverable should be ingredient and catalog correctness, not ranking sophistication. Once catalog data is trustworthy, add a deterministic 3-day planner, durable plan storage, alternatives, normal meal logging, raw interaction events, and controlled rollout. Keep the current `/v1/meal-suggestions` AI feature unchanged.

## Research Scope

- Feature: new catalog-backed meal recommendation flow.
- Output: 3 days, 3 meals per day, 5 alternatives per slot.
- Cuisines: Vietnamese, Japanese, Korean.
- Nutrition: daily calories split equally across breakfast, lunch, dinner.
- Logging: user can log a recommended meal through the normal meal flow.
- Quality level: production-ready minimum suitable for controlled testing.
- Data state: no recipes currently stored in the database.

## Methodology

- Reviewed current repository architecture and ingredient/meal persistence paths.
- Reused approved product decisions from feature discovery.
- Evaluated scope using YAGNI, KISS, DRY, and existing Clean Architecture/CQRS boundaries.
- Research conducted: 2026-07-15.

## Current-State Findings

1. `food_reference` already provides the correct canonical nutrition base, including normalized names and per-100g macros.
2. Food-specific serving conversions already have a model, so quantity normalization should extend this path rather than introduce a parallel unit system.
3. Persisted meal food items already support `food_reference_id`, but the domain and mapper path does not consistently preserve it. This must be corrected before recommendation logging.
4. Existing meal suggestions are AI-driven and should remain a separate feature and contract.
5. Current feature flags are boolean. Cohort percentages or numeric settings require either PostHog or a separate configuration mechanism.
6. No recipe catalog exists, so recommendation quality initially depends more on catalog coverage and validation than behavioral ranking.

## Recommended Architecture

### One Ingredient Authority

- Keep `food_reference` as the canonical nutritional identity.
- Add or strengthen normalized aliases for ingredient matching.
- Reuse serving-size conversions for units such as piece, tablespoon, cup, and milliliter.
- Require every nutritionally meaningful recipe ingredient to resolve to `food_reference`.
- Permit unlinked ingredients only when explicitly marked display-only, such as optional garnish.
- Reject ambiguous or unsupported conversions during catalog publishing; never silently treat an unknown unit as grams.

### Versioned Recipe Catalog

- Store recipe identity separately from immutable recipe versions.
- A version owns cuisine, meal types, instructions, servings, ingredients, and computed nutrition.
- Each recipe ingredient stores canonical food reference, entered quantity/unit, resolved grams, and display text.
- Derive recipe calories from resolved macros using the backend calorie formula.
- Published versions become immutable so previously generated plans and logged meals remain reproducible.

### Durable Recommendation Plans

- Introduce a distinct `CatalogMealPlan` aggregate to avoid collision with existing AI meal-planning models.
- Persist the selected recipe version for every day and slot.
- Persist generation inputs and ranking metadata needed to reproduce or explain a result.
- Generate five deterministic alternatives per slot from the same eligible catalog snapshot.
- Make create/retry behavior idempotent to avoid duplicate active plans.

### Logging and Measurement

- Convert a selected recipe version into normal meal food items with macro snapshots.
- Preserve `food_reference_id` on logged ingredients for future history matching.
- Record raw events for plan viewed, alternative viewed, swap selected, and meal logged.
- Start with logging-based success measurement. Do not add a separate cooked/completed state yet.

## High-Level Work Order

### 1. Lock Contracts and Invariants

- Define new API boundary without changing existing meal-suggestion endpoints.
- Define calorie, timezone, plan lifecycle, idempotency, and logging rules.
- Add regression tests for the existing AI suggestion and meal logging contracts.

### 2. Consolidate Ingredient Identity

- Preserve `food_reference_id` across ORM, domain, mapper, and API boundaries.
- Define alias resolution and strict quantity-to-gram conversion.
- Add validation for missing foods, ambiguous aliases, invalid units, and incomplete nutrition.

### 3. Build the Curated Recipe Catalog

- Add recipe, recipe-version, and recipe-ingredient persistence.
- Build a repeatable seed/import and validation pipeline.
- Prepare 180-270 reviewed recipes over time.
- Controlled-launch gate: at least 12 eligible recipes per cuisine and meal-type segment, and at least 72 unique published recipes.

### 4. Implement Deterministic Recommendation Logic

- Filter by cuisine, meal type, publication state, and nutrition validity.
- Score against the slot calorie target and avoid repetition across the 3-day plan.
- Add conservative history affinity only when linked meal history exists.
- Use stable tie-breaking so requests are testable and reproducible.

### 5. Persist Plans and Alternatives

- Store the generated 3-day plan and selected recipe versions.
- Support read, regenerate, and swap operations with clear lifecycle rules.
- Protect concurrent swaps and duplicate generation requests.

### 6. Add API, CQRS, and Normal Meal Logging

- Route commands and queries through the existing event bus and async unit of work.
- Return `allergy_evaluated: false`; do not imply allergy safety.
- Log selected recipes through the existing meal model with immutable nutrition snapshots.

### 7. Add Rollout and Observability

- Default the feature off.
- Use boolean backend gating plus PostHog exposure/cohort control where needed.
- Track catalog eligibility, generation latency, empty slots, swaps, logging conversion, and failures.
- Keep raw interaction events so ranking can improve later without schema replacement.

### 8. Verify Before Controlled Launch

- Unit-test conversion, nutrition, ranking, diversity, and idempotency rules.
- Integration-test migrations, persistence, CQRS registration, logging, and concurrent swaps.
- Run catalog validation as a release gate.
- Test with internal users before increasing rollout.

## Explicit Non-Goals for MVP

- No replacement of the existing AI meal-suggestion feature.
- No runtime AI recipe generation or external recipe lookup.
- No Redis recommendation cache initially.
- No embeddings or vector search for recipes.
- No learned popularity score, exploration algorithm, or ranking cron before interaction volume exists.
- No allergy filtering or allergy-safety claims.
- No undo workflow or separate cooked-completion state.
- No mobile implementation in this backend scope; only stable mobile-facing contracts.

## Main Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Duplicate ingredient identities | One canonical `food_reference` authority plus aliases |
| Incorrect nutrition from units | Strict food-specific conversion and publish-time rejection |
| Weak cold-start recommendations | Catalog coverage gates and deterministic nutrition/diversity scoring |
| Historical plans change after recipe edits | Immutable published recipe versions |
| Logged meals lose ingredient identity | Preserve `food_reference_id` end to end |
| Feature appears allergy-safe | Explicit `allergy_evaluated: false` contract |
| Premature ranking complexity | Store raw events now; defer learned ranking |

## Success Criteria

- Every published nutritional ingredient resolves to one canonical food reference.
- Every published recipe has reproducible gram amounts, macros, and derived calories.
- Backend returns a complete deterministic 3-day plan with five valid alternatives per slot.
- A recommendation can be logged as a normal meal without losing ingredient identity.
- Existing AI meal suggestions and meal logging remain backward compatible.
- Feature can be enabled for a controlled cohort and measured through logs/events.

## Repository References

- `README.md`
- `src/infra/database/models/food_reference_model.py`
- `src/infra/database/models/food_reference_serving_size.py`
- `src/infra/database/models/nutrition/food_item.py`
- `src/infra/mappers/meal_mapper.py`
- `src/api/routes/v1/meal_suggestions.py`
- `src/api/routes/v1/feature_flags.py`

## Next Steps

1. Review and approve this high-level direction.
2. Use `ck:plan hard` to convert it into phased implementation files with exact code ownership, migrations, APIs, and tests.
3. Resolve the remaining catalog-operation decisions before implementation starts.

## Unresolved Questions

- What licensed or internally owned source will supply the initial recipe content?
- Will initial catalog publishing use migrations/seed files only, or require an admin workflow?
- Should regenerating a plan replace the active plan or create a separately retained revision?
