---
title: Meal Recommendation Performance Redesign
type: brainstorm
status: approved
date: 2026-07-20
---

# Meal Recommendation Performance Redesign

## Summary

Current latency is mostly repeated database hydration, response expansion, and
request-bound analytics. Deterministic ranking is not the primary bottleneck:
the 180-meal optimizer benchmark measured p50 3.19 ms and p95 4.05 ms.

Approved direction: compiled catalog snapshot, compact plan reads and mutation
responses, aggregate affinity queries, non-blocking analytics, and immediate
mobile rendering from the last stored plan.

## Problem

- Generation loads every active catalog meal plus ingredients, food references,
  and serving-size rows. Cost grows linearly with catalog size.
- App initialization automatically waits for a plan read or new generation.
- Plan reads hydrate and serialize 9 selected meals plus 45 alternatives, each
  with full macros and ingredient lists.
- Log loads and locks the full plan twice, fetches the selected catalog meal
  again, persists an unnecessary placeholder image, reloads the normal meal,
  then returns the full plan.
- Swap locks and returns the full plan for a one-slot mutation.
- PostHog capture runs synchronously in the response path.

## Requirements

- Preserve deterministic recommendations and stable tie-breaking.
- Preserve four-table persistence and operation replay.
- Keep `food_reference` as canonical ingredient and nutrition authority.
- Keep calories backend-derived from macros; do not add a client calorie source.
- Preserve the separate AI `/v1/meal-suggestions` flow.
- Support at least 1,000 active catalog meals without full-catalog hydration per
  recommendation request.
- Avoid making mobile home-screen rendering depend on network completion.

## Scope

### Included

- Create, read, swap, and log recommendation paths.
- Catalog and user-affinity data preparation.
- Response payload shape and mobile state updates.
- Stage-level latency measurement.

### Excluded

- Learned ranking, vector search, or runtime LLM generation.
- Replacing the existing meal-suggestions feature.
- Background plan scheduling in the first performance slice.
- Changing recommendation product rules or calorie allocation.

## Findings

### Generate

`AsyncCatalogMealRepository.list_active_meals()` loads every active catalog row
and its complete nutrition dependency graph. Nutrition conversion repeats for
every ingredient on each request. History personalization separately hydrates up
to 5,000 meals across 90 days. The optimizer then performs repeated rankings,
but this CPU portion is small at the current catalog size.

### App load

The mobile recommendation provider starts `_loadBackendPlan()` immediately. A
stored plan triggers a full GET; a missing or expired plan triggers full
generation. No locally rendered stale plan shields the screen from network time.

### Read and mutation responses

All operations use `MealRecommendationPlanResponse`. Therefore a single-slot log
or swap returns the complete plan, including all alternative meal details and
ingredients. This amplifies database reads, serialization, transfer size, and
mobile parsing/state replacement.

### Log

The log command hydrates the full batch for `claim_slot_log()`, loads the selected
catalog meal again, saves and reloads a normal meal, hydrates the full batch again
for `finalize_slot_logged()`, and finally serializes the full plan.

## Evaluated Approaches

| Approach | Advantages | Costs | Decision |
|---|---|---|---|
| Tactical cleanup only | Smallest change; removes obvious blocking work | Generation still scales with full catalog | First phase only |
| Compiled catalog plus compact APIs | Removes repeated catalog work; fixes create/read/log/swap; handles thousands | Requires backend and mobile contract changes | Approved |
| Background plan generation | Best perceived generation latency | Jobs, retries, stale-state rules, operational overhead | Defer |

## Approved Design

### 1. Compiled catalog snapshot

- Build an immutable in-process catalog index on first use.
- Snapshot contains display fields, backend-computed macros, ingredient IDs,
  eligible meal types, cuisine, and active status.
- Refresh on bounded TTL and catalog revision change; imports are infrequent, so
  short catalog staleness is acceptable.
- Each backend worker owns one snapshot. Do not introduce Redis recommendation
  result caching in the first slice.
- Generation does not hydrate the catalog from SQL unless refreshing the index.

### 2. Aggregate affinity projection

- Replace full meal-domain hydration with one owner-scoped aggregate query.
- Return only linked `food_reference_id`, eaten timestamp/date, and effective
  quantity needed for recency weighting.
- Cache the resulting daily affinity profile briefly by user and local date when
  safe; invalidate after relevant meal logging.

### 3. Reduced ranking passes

- Partition candidates once by meal type.
- Compute stable scores once for each meal-type target.
- Select winners by filtering already selected IDs from the ranked lists.
- Select alternatives from the same rankings after all winners are known.
- Preserve current scoring weights, tolerance behavior, and deterministic order.

### 4. Compact plan contract

- Active-plan/home response returns plan metadata and 9 selected slot summaries:
  identity, name, image, calories, macros, selection version, and log status.
- Ingredient lists and full meal details load only for the opened meal/slot.
- Alternatives and ingredient-heavy meal details load through one owner-scoped
  slot-detail endpoint.
- Replace the current unreleased full-plan response directly; do not add
  representation flags or compatibility branches.

### 5. Delta mutation responses

- Swap locks and loads only candidates for the target slot.
- Log locks and loads only the target selected candidate plus required anchor
  metadata.
- Reuse the already loaded catalog snapshot during meal materialization.
- Do not create a placeholder image when the catalog meal has no real image.
- Mark the recommendation logged in the same transaction as normal meal
  persistence.
- Return slot delta fields instead of the full plan: `slot_id`, selected catalog
  meal, `selection_version`, and `logged_meal_id` as applicable.
- Mobile applies the delta to its existing plan state.

### 6. Non-blocking analytics and stage metrics

- Remove PostHog network calls from response completion.
- Reuse an analytics client or enqueue bounded background delivery.
- Record latency for target lookup, affinity query, catalog refresh, ranking,
  persistence, hydration, serialization, and analytics enqueue.

### 7. Mobile stale-while-revalidate

- Persist the last successful plan payload, not only its ID.
- Render it immediately on provider initialization.
- Refresh in the background and replace state only when a newer plan arrives.
- Keep slot-level mutation indicators; avoid replacing the full plan after a
  successful log or swap.

## Target Flow

1. Mobile renders last persisted plan immediately.
2. Backend reads active plan summary or validates client plan version.
3. New generation reads lightweight daily target and aggregate affinity.
4. Planner uses warm compiled catalog and performs bounded ranking.
5. Backend bulk-persists candidates and returns compact plan payload.
6. Log and swap operate on one slot and return deltas.
7. Analytics delivery occurs outside response latency.

## Success Metrics

- Existing active-plan read p95 below 300 ms.
- Log and swap p95 below 300 ms.
- Warm generation p95 below 500 ms.
- Cold catalog refresh plus generation p95 below 1 second.
- Home screen displays persisted recommendations without waiting for network.
- No full-catalog SQL hydration on warm generation.
- No full-plan hydration for log or swap.
- Same selected meal IDs for existing deterministic characterization fixtures.
- Catalog size benchmark passes at 180, 1,000, and 5,000 meals.

## Risks

| Risk | Mitigation |
|---|---|
| Stale catalog snapshot | Short TTL plus revision check; refresh after import |
| Multi-worker snapshot divergence | Deterministic revision and bounded TTL |
| Backend/mobile contract drift | Change backend and mobile together and lock one HTTP contract with integration tests |
| Delta mutation race | Keep selection version and transactional row locks |
| Affinity cache staleness after logging | Invalidate user/date key after meal write |
| Hidden DB latency remains | Stage-level metrics and query-count tests before/after |

## Touchpoints

- `src/api/routes/v1/meal_recommendations.py`
- `src/api/routes/v1/meal_recommendation_route_support.py`
- `src/api/schemas/response/meal_recommendation_responses.py`
- `src/app/handlers/command_handlers/meal_recommendation/`
- `src/app/services/meal_recommendation_history_projector.py`
- `src/app/services/recommended_meal_materialization_service.py`
- `src/domain/services/meal_recommendation/`
- `src/infra/repositories/catalog_recipe_repository_async.py`
- `src/infra/repositories/meal_recommendation_plan_repository_async.py`
- Mobile `meal_recommendation_controller.dart`, repository, data source, models,
  mappers, and targeted tests.

## Next Steps

1. Create tests-first implementation plan covering backend contracts, repository
   query shape, compiled catalog lifecycle, metrics, and mobile migration.
2. Capture representative test/staging baselines before changing behavior.
3. Ship tactical request-path cleanup before catalog-index changes.
4. Verify each phase with endpoint latency, SQL count, payload size, and mobile
   render timing.

## Unresolved Questions

- Exact staging p50/p95 baseline unavailable from local environment.
