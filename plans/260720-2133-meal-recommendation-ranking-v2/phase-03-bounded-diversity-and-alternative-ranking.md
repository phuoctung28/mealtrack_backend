---
phase: 3
title: "Bounded Diversity And Alternative Ranking"
status: completed
priority: P1
effort: "2-2.5d"
dependsOn: [2]
---

# Phase 3: Bounded Diversity And Alternative Ranking

## Context Links

- [Plan overview](./plan.md)
- [Normalized scoring phase](./phase-02-snapshot-idf-and-normalized-scoring.md)
- [Approved bounded rerank design](../reports/260720-2112-meal-recommendation-ranking-v2-brainstorm.md)
- [Current optimizer](../../src/domain/services/meal_recommendation/three_day_plan_optimizer.py)
- [Current alternative service](../../src/domain/services/meal_recommendation/slot_alternative_service.py)

## Overview

- **Priority:** P1.
- **Status:** Completed.
- **Goal:** finish deterministic selection by adding an IDF-weighted diversity component over a fixed shortlist, then contextualize each slot's alternatives against the other eight winners.
- **Boundary:** hard eligibility and calorie fallback run before diversity and cannot be traded away.

## Key Insights

- A full pairwise catalog comparison would undo the merged rank-once performance work; every contextual pass must be capped at 30 candidates.
- `diversity_fit = 1 - max(weighted_overlap(candidate, comparison_meal))`; an empty comparison set receives one constant value so the first slot's base order does not change.
- Winners are chosen sequentially in the existing day/meal-type order. Alternatives are recomputed only after all nine winners are fixed.
- Each alternative excludes all nine selected IDs and compares with the other eight winners, not with its own slot winner twice.
- Persist the contextual final score so the stored plan is auditable without later recomputation.

## Requirements

### Functional

- Preserve current supported-catalog filtering, unique selected IDs, `20%` and `30%` tolerance gates, and absolute-calorie fallback.
- After eligibility/fallback, take at most the first 30 candidates in deterministic v2 base-score order.
- Define IDF-weighted Jaccard overlap over unique canonical ingredient sets as `sum(idf(intersection)) / sum(idf(union))`; it is symmetric, bounded to `[0,1]`, and `0` when the union has zero total weight.
- Set `diversity_fit = 1 - maximum overlap` against already selected winners.
- The first winner receives constant `diversity_fit = 1.0` for every candidate so diversity cannot reorder it.
- Final score uses the approved `calorie + ingredient + diversity` weights and ties by catalog meal ID.
- Build exactly 9 unique winners and 5 alternatives per slot when catalog sufficiency allows.
- For each slot, alternatives come from its eligible top-30 remaining pool, exclude all winners, compare against the other eight winners, and persist their contextual scores.
- Return the same typed insufficiency outcomes when fewer than 9 unique meals or fewer than 5 alternatives are available.

### Non-Functional

- No randomness, wall clock, database call, mutable global, or catalog-wide pairwise pass.
- Worst contextual work is bounded by `9 * 30` candidate evaluations plus `9 * 30 * 8` winner comparisons, each over canonical ID sets.
- Identical algorithm version, catalog snapshot, daily calories, cuisines, and affinity produce identical ordered IDs and six-decimal scores regardless of input ordering.

## Architecture And Data Flow

```text
per meal type: full v2 base rank once

for each of 9 slots:
  selected-ID filter -> calorie tolerance/fallback -> first 30
  -> compare candidate with prior winners
  -> final contextual score -> stable winner

after 9 winners:
  for each slot: selected-ID filter -> calorie tolerance/fallback -> first 30
  -> compare candidate with other 8 winners
  -> final contextual score -> first 5 alternatives
```

## Related Code Files

### Add

- `src/domain/services/meal_recommendation/plan_diversity_reranking_service.py`
- `tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py`

### Modify

- `src/domain/services/meal_recommendation/recipe_scoring_service.py`
- `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- `src/domain/services/meal_recommendation/slot_alternative_service.py` or remove its duplicated path only if all callers are migrated in the same phase.
- `tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py`
- `scripts/testing/benchmark_meal_recommendation_performance.py`

### Delete

- None by default. Delete `slot_alternative_service.py` only if live caller search proves it becomes unused and its behavior is fully represented by the bounded reranker.

## Implementation Steps

1. Write pure overlap tests for identical, disjoint, partial, common-versus-rare, duplicate, empty, symmetry, bound, and input-order cases.
2. Write shortlist tests with more than 30 eligible candidates and an instrumented reranker proving candidate index 31 is never contextually evaluated.
3. Add winner-selection tests proving hard tolerance is applied before shortlist/diversity and a diverse but calorie-ineligible meal cannot win.
4. Add first-slot tests proving constant diversity preserves the base ranking.
5. Add full-plan v2 goldens for cold, sparse, medium, and dense history, including stable six-decimal winner and alternative scores.
6. Add alternative tests proving all nine winners are excluded, exactly the other eight winners form the comparison context, and no more than 30 alternatives are evaluated per slot.
7. Implement the pure diversity reranking service with named shortlist constant `30`, stable catalog-ID tie-break, and unique canonical ID sets.
8. Refactor the optimizer so v1 retains its existing selection path while v2 calls the bounded contextual path; keep shared hard eligibility/fallback helpers single-sourced.
9. Generate alternatives only after winners are final and persist the returned contextual score already carried by the domain plan.
10. Extend the synthetic benchmark to exercise both v1 and v2 and report algorithm, catalog size, generation p50/p95, and evaluation counts.
11. Run domain, handler, contract, benchmark, lint, and import-boundary gates.

## Todo List

- [x] Weighted overlap math is pure, bounded, and test-locked.
- [x] Hard calorie gates precede diversity.
- [x] Winner rerank evaluates at most 30 candidates per slot.
- [x] Alternatives compare against exactly the other eight winners.
- [x] V2 goldens cover cold through full-confidence history.
- [x] 9 unique winners and 45 alternatives remain invariant.
- [x] V1 goldens remain unchanged.

## Tests Before

```bash
.venv/bin/python -m pytest -q \
  tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py \
  tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py
```

New overlap, shortlist-cap, contextual winner, and alternative tests must fail before implementation while v1 tests stay green.

## Refactor

- Consolidate tolerance and selected-ID filtering into one tested helper used by v1 and v2; behavior must remain version-neutral.
- Keep component scoring separate from contextual selection so base pools are still ranked once.
- Remove obsolete alternative code only after `rg` proves no live imports and regression tests cover the replacement.
- Split the optimizer instead of allowing a touched Python file to exceed the repository's 400-line hard cap.

## Tests After

```bash
.venv/bin/python -m pytest -q \
  tests/unit/domain/services/meal_recommendation/test_catalog_ingredient_statistics_service.py \
  tests/unit/domain/services/meal_recommendation/test_plan_diversity_reranking_service.py \
  tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py \
  tests/unit/api/test_meal_recommendation_http_contract.py
.venv/bin/python scripts/testing/benchmark_meal_recommendation_performance.py \
  --catalog-sizes 180,1000,5000 \
  --output plans/reports/meal-recommendation-ranking-v2-local.json
.venv/bin/ruff check \
  src/domain/services/meal_recommendation \
  tests/unit/domain/services/meal_recommendation \
  scripts/testing/benchmark_meal_recommendation_performance.py
.venv/bin/lint-imports
```

## Regression Gate

- Phase 1 v1 goldens and Phase 2 scoring/statistics tests pass without expectation drift.
- Instrumented tests prove the fixed shortlist cap, not merely benchmark speed.
- No API, response, persistence schema, catalog import, history SQL, or mobile change.
- Synthetic 5,000-meal v2 generation remains below the existing warm `<500 ms` gate locally; staging is still required for production promotion.

## Success Criteria

- [x] V2 reduces repeated canonical ingredient patterns in its controlled fixtures without violating calorie eligibility.
- [x] First-slot ordering is identical to the v2 base score order.
- [x] Winner and alternative contextual scores are deterministic and persisted-ready.
- [x] Complexity remains bounded and does not become full-catalog pairwise ranking.
- [x] V1 remains an operationally usable, verified fallback.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Diversity overrules nutrition | Apply tolerance/fallback before shortlist and retain at least 55% calorie weight. |
| Shortlist cap exists only by convention | Instrument evaluator call counts in unit tests. |
| Alternatives receive wrong context | Assert exact eight-winner context for every slot. |
| Tie/order drift across runtimes | Stable iteration, explicit catalog-ID tie-break, final six-decimal rounding. |
| Optimizer becomes hard to maintain | Separate pure overlap/reranking service and shared eligibility helper. |

## Security Considerations

- Domain reranking receives reduced catalog and affinity data only.
- Do not log candidate IDs, ingredient IDs, overlap pairs, or user vectors.
- No external similarity service, embeddings, or user-to-user data comparison.

## Next Steps

Wire the verified v2 optimizer into new plan generation without changing stored or public contracts.

## Unresolved Questions

- None.
