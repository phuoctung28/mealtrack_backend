---
type: brainstorm
date: 2026-07-20
status: approved
scope: meal-recommendation-ranking-v2
branch: delivery
source: 2024.paclic-1.4
---

# Brainstorm: Meal Recommendation Ranking V2

## Summary

Evolve `catalog_deterministic_v1` without replacing the merged recommendation or performance architecture. Keep nutrition eligibility hard, replace raw ingredient-weight summation with normalized canonical-ingredient similarity, then add bounded plan-diversity reranking. Ship as `catalog_deterministic_v2` behind versioned rollout and preserve v1 fallback.

No distance, store, map, text-ranking, collaborative-filtering, vector, LLM, schema, or endpoint work in this design.

## Problem Statement

Current scorer uses 82% calorie fit plus 18% summed ingredient affinity. It is deterministic and cheap, but raw summation:

- favors meals with more matched ingredients;
- lets ubiquitous ingredients dominate;
- does not normalize user and meal profiles;
- prevents plan diversity from influencing selection.

PACLIC 2024 ViFoodRec supports ingredient-heavy content ranking as a useful direction, but its direct composite design solves dish similarity, not MealTrack's constrained three-day planning. Copying BM25, TF-IDF, Pearson, Jaccard, and collaborative filtering would add unjustified complexity for the curated catalog.

## Confirmed Requirements

- Work from merged `delivery` after recommendation PR #420 and performance PR #422.
- Preserve backend-derived calories, canonical `food_reference_id`, and deterministic output.
- Preserve the four recommendation tables and separate `/v1/meal-suggestions` behavior.
- Preserve compact plan summaries, lazy slot detail, and changed-slot swap/log responses.
- Preserve process-local catalog snapshots, aggregate 90-day affinity queries, and one-pass meal-type ranking pools.
- Keep the approved starting weights: confidence-scaled ingredient affinity up to 35%, diversity 10%, remaining weight calorie fit.
- Produce design only. Implementation requires a separate approved plan.

## Merged Branch Findings

### Public Contract

Five catalog-recommendation endpoints now exist:

1. `POST /v1/meal-recommendations/three-day`
2. `GET /v1/meal-recommendations/{plan_id}`
3. `GET /v1/meal-recommendations/{plan_id}/slots/{slot_id}`
4. `POST /v1/meal-recommendations/{plan_id}/slots/{slot_id}/swap`
5. `POST /v1/meal-recommendations/{plan_id}/slots/{slot_id}/log`

Create/read return compact summaries. Slot detail, swap, and log return one detailed slot. Ranking v2 must not change these shapes.

### Performance Contract

- Active catalog loads through `CatalogMealSnapshotService` with revision checks, TTL reuse, single-flight refresh, and last-good fallback.
- History projection uses one aggregate 90-day query before domain scoring.
- Optimizer builds one ranked pool per meal type and reuses it for winners and alternatives.
- Current local 5,000-meal synthetic generation p95 is about 55 ms; staging request-path p95 evidence remains pending.
- Existing gates remain: warm generation p95 below 500 ms; compact read and changed-slot mutation p95 below 300 ms.

## Evaluated Approaches

### Keep V1 Unchanged

Pros:

- Lowest implementation and rollout risk.
- Already deterministic and fast.

Cons:

- Ingredient-set size bias remains.
- Common ingredients dominate.
- Three-day plans can repeat similar ingredient patterns.

Decision: retain as fallback and control cohort, not final direction.

### Copy ViFoodRec Composite Ranking

Use description, ingredients, nutrition, tags, Cosine, Pearson, BM25, Jaccard, and TF-IDF.

Pros:

- Mirrors the paper's strongest reported experiment.
- Broad offline experimentation surface.

Cons:

- Raw Vietnamese text is weaker than MealTrack's canonical ingredient IDs.
- Pairwise multi-metric work fights merged snapshot/rank-once performance design.
- No dense trustworthy ratings exist for collaborative filtering.
- Harder to explain, test, and operate.

Decision: rejected for production v2.

### Canonical Similarity Plus Bounded Diversity

Keep hard constraints, compute normalized ingredient similarity from canonical IDs, and rerank a fixed shortlist for plan diversity.

Pros:

- Uses MealTrack's strongest data.
- Fixes current normalization flaw.
- Remains deterministic and explainable.
- Fits process-local snapshots and one-pass ranked pools.
- No DB or API changes.

Cons:

- Requires new golden fixtures and score-version discipline.
- Diversity adds bounded per-slot work.
- Starting weights remain hypotheses requiring outcome validation.

Decision: selected.

## Recommended Design

### Stage 1: Hard Eligibility

Keep current rules unchanged:

- active/published catalog meal;
- supported meal type and cuisine filter;
- derived calories greater than zero;
- unique selected meals across nine slots;
- prefer +/-20% calorie tolerance, then +/-30%, then deterministic absolute calorie-deviation fallback.

Nutrition eligibility is never traded against personalization.

### Stage 2: Catalog Ingredient Statistics

Build immutable statistics once per catalog snapshot revision:

```text
idf(i) = ln((catalog_size + 1) / (meals_containing_i + 1)) + 1
```

Common ingredients receive lower influence. Statistics stay process-local beside the immutable catalog snapshot; no persistence table or external vector store.

### Stage 3: Normalized Ingredient Similarity

Use the aggregate 90-day affinity profile as the user vector:

```text
user(i) = normalized_history_weight(i) * idf(i)
meal(i) = idf(i) when the meal contains ingredient i, otherwise 0
ingredient_fit = cosine(user, meal)
```

Both vectors are normalized. `ingredient_fit` remains within `[0, 1]`. Missing or insufficient canonical history yields `ingredient_fit = 0` and `confidence = 0`.

Do not add fuzzy name matching. Only canonical `food_reference_id` participates.

### Stage 4: Confidence-Scaled Base Score

```text
affinity_weight = 0.35 * history_confidence
diversity_weight = 0.10
calorie_weight = 0.90 - affinity_weight

score =
  calorie_weight * calorie_fit
  + affinity_weight * ingredient_fit
  + diversity_weight * diversity_fit
```

Behavior by confidence:

| History confidence | Calorie | Ingredient | Diversity |
|---:|---:|---:|---:|
| 0.0 | 90% | 0% | 10% |
| 0.5 | 72.5% | 17.5% | 10% |
| 1.0 | 55% | 35% | 10% |

This protects cold start and interpolates gradually instead of switching algorithms.

### Stage 5: Bounded Diversity Rerank

Preserve one full ranked pool per meal type. For each slot:

1. Apply current tolerance and selected-ID filters.
2. Take a fixed deterministic shortlist of the top 30 remaining candidates.
3. Compute IDF-weighted ingredient overlap against already selected plan meals.
4. Set `diversity_fit = 1 - maximum_weighted_overlap`.
5. Sort by final score descending, then stable catalog meal ID ascending.

The first slot receives a constant diversity value, so diversity does not change its order. Full-catalog pairwise comparison is forbidden.

After nine winners are fixed, select each slot's five alternatives from its top-30 eligible pool, scored against the other eight selected meals. Persist the contextual final score with the candidate.

### Stage 6: Versioning And Replay

- New plans use `algorithm_version = catalog_deterministic_v2` only when enabled.
- Existing v1 plans retain stored scores, selections, alternatives, and replay behavior.
- Idempotent replay never recalculates a persisted plan under a newer algorithm.
- Same algorithm version, catalog revision, target, and affinity input must yield the same ordered output.

## Integration Touchpoints

Likely modifications in a later implementation plan:

- `src/domain/services/meal_recommendation/recipe_scoring_service.py`
- `src/domain/services/meal_recommendation/ingredient_affinity_service.py`
- `src/domain/services/meal_recommendation/three_day_plan_optimizer.py`
- `src/domain/services/meal_recommendation/slot_alternative_service.py`
- `src/app/services/catalog_meal_snapshot_service.py`
- `src/app/handlers/command_handlers/meal_recommendation/create_three_day_meal_recommendation_command_handler.py`
- `tests/unit/domain/services/meal_recommendation/test_deterministic_recommendation_domain.py`
- `tests/unit/app/services/test_catalog_meal_snapshot_service.py`
- `tests/unit/app/handlers/test_meal_recommendation_handlers.py`

No route, response schema, database migration, catalog import, mobile contract, or existing AI suggestion file should change.

## Rollout Strategy

### Offline Characterization

- Freeze v1 golden selections for cold, sparse, medium, and dense affinity histories.
- Add invariants for score bounds, stable ties, calorie tolerances, nine winners, and 45 alternatives.
- Benchmark 180, 1,000, and 5,000 meals using the merged performance harness.

### Shadow Evaluation

- Keep v1 user-visible.
- Sample bounded requests and compute v2 from immutable snapshot plus reduced affinity input without persistence side effects.
- Record only bounded aggregate comparisons: selection overlap, calorie deviation, ingredient-fit delta, repeated-ingredient delta, generation duration, and insufficiency.
- Never emit ingredient IDs, raw history, meal names, or precise user data to analytics.

### Controlled Promotion

- Promote v2 through deterministic server-side cohorting.
- Keep v1 as instant rollback.
- Compare plan-to-log rate, swap-away rate, catalog coverage, calorie deviation, repeated-ingredient rate, insufficiency, and p95 latency.
- Do not add learned ranking until real outcome volume supports time-split offline evaluation.

## Success Metrics And Acceptance Criteria

- 100% hard nutrition, uniqueness, owner-scope, idempotency, and replay invariants preserved.
- Same inputs under v2 produce identical ordered identities and scores at declared numeric precision.
- Cold start remains valid and deterministic with zero linked history.
- Common ingredients no longer dominate similarity.
- Diversity rerank examines at most 30 candidates per slot.
- No new SQL on warm catalog access beyond the existing aggregate history and persistence flow.
- Existing five endpoint paths and compact/detail/delta response shapes remain unchanged.
- Local 5,000-meal benchmark stays within merged performance gates and shows no superlinear full-pool reranking.
- V2 remains reversible by algorithm configuration without mutating existing plans.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Common staples still dominate | Homogeneous plans | Snapshot-level IDF plus weighted overlap |
| Diversity reduces calorie fit | Nutrition regression | Apply current tolerance gates first; calorie retains at least 55% weight |
| Sparse history creates unstable personalization | Unexpected ranking | Confidence-scaled affinity and calorie-first fallback |
| Dynamic rerank erodes PR #422 gains | Latency regression | Fixed top-30 shortlist; benchmark 180/1,000/5,000 |
| Score meaning changes across versions | Replay/audit confusion | Persist explicit algorithm version and never recalculate old plans |
| Shadow evaluation leaks personal food history | Privacy issue | Aggregate metrics only; no ingredients or raw history in events |

## Explicit Non-Goals

- Store, restaurant, availability, location, map, or distance dimensions.
- ViFoodRec dataset ingestion.
- Description/tag BM25 or TF-IDF ranking.
- Embeddings, Pinecone, pgvector, or a vector database.
- Collaborative filtering, learned popularity, bandits, or LLM ranking.
- New endpoints, tables, migrations, or mobile response fields.
- Allergy-policy expansion or recipe/catalog redesign.

## Next Steps

1. Create `/ck:plan --tdd` from this report because ranking changes critical business logic with strong regression coverage.
2. Characterize v1 before changing score behavior.
3. Implement and validate v2 behind explicit algorithm selection.
4. Run shadow comparison before any user-visible cohort.

## Unresolved Questions

- None. Initial weights are experiment defaults and require shadow/cohort evidence before broad promotion.
