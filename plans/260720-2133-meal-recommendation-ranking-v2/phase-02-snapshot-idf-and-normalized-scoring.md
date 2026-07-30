---
phase: 2
title: "Snapshot IDF And Normalized Scoring"
status: completed
priority: P1
effort: "2-2.5d"
dependsOn: [1]
---

# Phase 2: Snapshot IDF And Normalized Scoring

## Context Links

- [Plan overview](./plan.md)
- [Contract characterization](./phase-01-contract-and-golden-characterization.md)
- [Approved ranking equations](../reports/260720-2112-meal-recommendation-ranking-v2-brainstorm.md)
- [Catalog snapshot service](../../src/app/services/catalog_meal_snapshot_service.py)
- [Affinity service](../../src/domain/services/meal_recommendation/ingredient_affinity_service.py)

## Overview

- **Priority:** P1.
- **Status:** Completed.
- **Goal:** derive immutable catalog ingredient statistics once per snapshot revision and introduce a v2 base scorer using normalized canonical-ingredient cosine similarity.
- **Boundary:** v1 remains the default behavior throughout this phase.

## Key Insights

- `CatalogMealSnapshotService` already owns revision, TTL, single-flight refresh, and last-good fallback; statistics must share the exact same immutable lifetime as `meals`.
- History weights are already normalized and confidence is already bounded to `[0,1]`; v2 uses confidence for component weights, not by multiplying cosine twice.
- IDF document frequency counts unique canonical ingredient presence per active snapshot meal, not grams, occurrences, labels, or serving text.
- V2 base ranking is still full-pool `O(total ingredient links)` once per meal-type pool; diversity work is deferred to Phase 3.

## Requirements

### Functional

- Add immutable `CatalogIngredientStatistics` with catalog size and `idf_by_food_reference_id`.
- Calculate `idf(i) = ln((N + 1) / (df_i + 1)) + 1` over all active meals in the immutable snapshot.
- Count an ingredient at most once per meal; ignore non-positive IDs; return deterministic empty statistics for an empty input in pure unit tests.
- Build statistics only when snapshot meals are loaded or reloaded; same-revision TTL extension and warm reads reuse the identical object.
- Compute user vector component `history_weight(i) * idf(i)` and meal vector component `idf(i)` for canonical presence.
- Return cosine in `[0,1]`; missing history, zero norms, or no overlap returns `0`.
- Apply approved weights exactly: `affinity=0.35*confidence`, `diversity=0.10`, `calorie=0.90-affinity`.
- Produce v2 base score components without changing v1 score behavior.

### Non-Functional

- Domain statistics/scoring code has no SQL, framework, settings, observability, or external-library dependency.
- Numeric outputs are finite and rounded only at the final persisted score boundary to six decimals.
- Warm snapshot access performs no additional SQL or statistics rebuild.

## Architecture And Data Flow

```text
catalog repository load
  -> immutable meals tuple
  -> pure CatalogIngredientStatisticsService.build(meals)
  -> CatalogMealSnapshot(revision, meals, ingredient_statistics, ttl)

aggregate history -> normalized affinity profile
snapshot statistics + meal canonical IDs
  -> cosine ingredient_fit
  -> confidence-scaled calorie/ingredient base components
```

The diversity component is represented as an explicit input to final scoring. Phase 2 uses a constant value so it cannot reorder the initial shortlist; Phase 3 supplies contextual values.

## Related Code Files

### Add

- `src/domain/services/meal_recommendation/catalog_ingredient_statistics_service.py`
- `tests/unit/domain/services/meal_recommendation/test_catalog_ingredient_statistics_service.py`

### Modify

- `src/app/services/catalog_meal_snapshot_service.py`
- `src/domain/services/meal_recommendation/recipe_scoring_service.py`
- `src/domain/services/meal_recommendation/ingredient_affinity_service.py` only if a small typed vector helper belongs with the profile; do not change profile construction semantics.
- `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py` to pass snapshot statistics without another catalog read.
- `tests/unit/app/services/test_catalog_meal_snapshot_service.py`
- `tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py`
- `scripts/testing/benchmark_meal_recommendation_performance.py` to select and label v1/v2 inputs when needed.

### Delete

- None.

## Implementation Steps

1. Write pure IDF tests for empty input, one meal, common versus rare ingredients, duplicate ingredient rows, invalid IDs, order independence, and the exact logarithmic equation.
2. Add snapshot tests proving statistics are constructed on cold load/revision change, reused on warm read/same-revision TTL extension, and retained with last-good fallback.
3. Implement the frozen statistics value object and pure builder in the domain layer; use sets per meal for document frequency.
4. Write cosine tests covering exact match, partial match, no overlap, common-versus-rare influence, duplicate meal ingredients, zero history, finite bounds, and scale invariance.
5. Extend the internal v2 score result with named calorie, ingredient, and diversity component values for tests and benchmark summaries; keep the persisted/public score contract unchanged.
6. Implement v2 scoring behind an explicit strategy/version input while keeping the existing constructor/default path bit-for-bit v1.
7. Test approved component weights at confidence `0`, `0.5`, and `1`, including their sum of `1.0` and cold-start ordering.
8. Feed snapshot statistics through the create path without adding repository reads; non-snapshot unit construction may derive statistics from its supplied immutable catalog fixture.
9. Run v1 goldens, new v2 scoring tests, snapshot tests, lint, and import-boundary checks.

## Todo List

- [x] IDF equation and document-frequency semantics are test-locked.
- [x] Statistics lifecycle equals snapshot lifecycle.
- [x] Cosine behavior and numeric bounds are test-locked.
- [x] Approved confidence-scaled weights are exact.
- [x] V1 remains the default and its goldens are unchanged.
- [x] Warm snapshot path has no new SQL or rebuild.

## Tests Before

Add failing v2 tests before creating the statistics service or v2 scorer.

```bash
.venv/bin/python -m pytest -q \
  tests/unit/domain/services/meal_recommendation/test_catalog_ingredient_statistics_service.py \
  tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py \
  tests/unit/app/services/test_catalog_meal_snapshot_service.py
```

Expected pre-implementation result: new v2 tests fail for missing behavior while all Phase 1 v1 characterizations remain green.

## Refactor

- Extract calorie-fit and canonical-ID-set helpers only after both v1 and v2 tests pass.
- Keep v1 raw affinity logic isolated; do not silently reinterpret v1 through the v2 cosine helper.
- Prefer frozen dataclasses and pure functions; avoid mutable caches outside the existing snapshot service.
- If a touched Python file approaches 200 lines, split statistics or component math into the new focused module rather than growing the optimizer.

## Tests After

```bash
.venv/bin/python -m pytest -q \
  tests/unit/domain/services/meal_recommendation/test_catalog_ingredient_statistics_service.py \
  tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py \
  tests/unit/app/services/test_catalog_meal_snapshot_service.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py
.venv/bin/ruff check \
  src/domain/services/meal_recommendation/catalog_ingredient_statistics_service.py \
  src/domain/services/meal_recommendation/recipe_scoring_service.py \
  src/domain/services/meal_recommendation/ingredient_affinity_service.py \
  src/domain/services/meal_recommendation/three_day_plan_optimizer.py \
  src/app/services/catalog_meal_snapshot_service.py \
  tests/unit/domain/services/meal_recommendation \
  tests/unit/app/services/test_catalog_meal_snapshot_service.py
.venv/bin/lint-imports
```

## Regression Gate

- Every Phase 1 v1 golden passes without updated expected values.
- Snapshot cold failure and last-good behavior remain unchanged.
- No new database call, migration, route field, response field, or mobile type.
- Calories continue to come from the existing backend-derived `CatalogMeal.calories` property.

## Success Criteria

- [x] Rare canonical ingredients influence similarity more than ubiquitous ingredients under the exact IDF formula.
- [x] Cosine removes matched-ingredient-count and vector-scale bias.
- [x] Confidence `0/0.5/1` yields weights `90/0/10`, `72.5/17.5/10`, and `55/35/10`.
- [x] Statistics are immutable and revision-consistent with the catalog snapshot.
- [x] V1 behavior remains a verified fallback.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Statistics and meals come from different revisions | Store both in one frozen snapshot created in one refresh branch. |
| Confidence applied twice | Test the equation and keep cosine independent from confidence. |
| Duplicate rows inflate IDF/meal norm | Deduplicate canonical IDs per meal before df or vector calculation. |
| Floating-point drift breaks replay expectations | Stable iteration, finite checks, catalog-ID tie-break, final six-decimal rounding. |

## Security Considerations

- Statistics contain catalog IDs only and never user history.
- Do not log IDF maps, affinity vectors, ingredient IDs, or raw meals.
- Domain layer stays dependency-free; no external vector store or network call.

## Next Steps

Use the verified v2 base components to implement bounded contextual diversity and alternative ranking.

## Unresolved Questions

- None.
