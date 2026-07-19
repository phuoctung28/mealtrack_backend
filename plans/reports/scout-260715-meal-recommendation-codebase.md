---
title: Catalog-Backed 3-Day Meal Recommendation Codebase Scout
date: 2026-07-16
status: complete
scope: read-only
branch: delivery
---

# Catalog-Backed 3-Day Meal Recommendation Codebase Scout

## Summary

The MVP has strong reusable nutrition/catalog primitives, but no active persistent meal-plan feature. `food_reference` can supply deterministic nutrition and serving conversions, yet it lacks meal-template semantics and its current name search has no stable order. The existing `food_item.food_reference_id` FK is not preserved by the domain, ORM mapper, edit, suggestion, or API paths. That preservation gap must be fixed before catalog-backed recommendations are saved as meals.

The safest new flow is a read-only CQRS query returning a response-only 3-day plan, backed by a pure deterministic domain service and an async catalog repository method with explicit eligibility filters and stable ordering. Persistence should be deferred unless explicitly required. Runtime rollout should use a default-off environment setting or the existing DB flag system; PostHog currently captures analytics but does not evaluate backend flags.

## Catalog and Serving-Size Seams

- `src/infra/database/models/food_reference_model.py:23-75` defines the canonical catalog: names/localization, category/region, per-100g macros, legacy serving JSON, source/verification, image, and normalized serving/nutrient relationships.
- `src/infra/database/models/food_reference_serving_size.py:9-37` defines ordered serving conversions with `grams`, `milliliters`, `is_default`, and `position`.
- `src/infra/repositories/food_reference_projection.py:34-58` is the established full catalog projection, including ID, macros, serving sizes, allowed units, source, verification, and image.
- `src/infra/repositories/food_reference_projection.py:61-86` normalizes serving aliases; `src/infra/repositories/food_reference_projection.py:112-145` prefers normalized rows, falls back to legacy JSON, and guarantees a gram unit.
- `src/infra/repositories/food_reference_repository_async.py:23-78` eagerly loads serving/nutrient children for ID, barcode, FDC, and name lookup.
- `src/infra/repositories/food_reference_repository_async.py:127-155` provides efficient batch/exact normalized-name lookup.
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py:354-380` is the reusable deterministic per-100g scaling formula; `src/domain/services/meal_suggestion/nutrition_lookup_service.py:526-541` preserves catalog IDs while scaling its intermediate values.
- `src/infra/database/uow_async.py:104-121` owns repository creation per async session. `src/infra/repositories/food_reference_uow_adapter.py:10-77` shows the fresh-UoW adapter pattern for callers outside a handler transaction.

### Determinism and catalog readiness gaps

- `src/infra/repositories/food_reference_repository_async.py:67-78` performs `ILIKE` plus `LIMIT` without `ORDER BY`; repeated calls are not guaranteed to return the same rows.
- There is no method to list eligible rows by category, region, verification, non-null macros, and usable serving conversion. The MVP needs explicit filters and an order such as category, normalized name, then ID.
- `src/infra/database/models/food_reference_model.py:28-56` has ingredient nutrition metadata but no meal type, recipe/template, dietary tag, allergen, preparation, or pairing fields. It cannot alone produce coherent deterministic meals unless the algorithm defines category slots or a new seeded meal-template layer is added.
- `src/infra/database/models/food_reference_serving_size.py:20-24` permits serving rows with both grams and milliliters null. Selection must reject unusable rows or deliberately use a 100g fallback.
- `src/infra/database/models/food_reference_model.py:30-32` keeps `name_normalized` nullable even though `migrations/versions/046_add_name_normalized_to_food_reference.py:19-29` added a unique index. Legacy null rows are invisible to exact/batch matching.
- `scripts/import_food_seeds.py:136-155` imports removed `FoodReferenceRepository` code and calls nonexistent `upsert_seed()`. `scripts/data/` contains no catalog JSON, so deployed catalog sufficiency is not currently reproducible from the repository.
- The migration backfill accepts fewer serving aliases at `migrations/versions/20260609000005_normalize_food_notification_payout_details.py:107-135` than runtime projection accepts at `src/infra/repositories/food_reference_projection.py:70-80`; some legacy rows may lack normalized serving children.

## `food_reference_id` Preservation

- DB support exists at `src/infra/database/models/nutrition/food_item.py:23-30` and was introduced at `migrations/versions/035_evolve_barcode_to_food_reference.py:83-95`.
- The domain `FoodItem` omits the field at `src/domain/model/nutrition/nutrition.py:10-24`; serialization at `src/domain/model/nutrition/nutrition.py:47-65` also omits it.
- ORM-to-domain mapping drops it at `src/infra/mappers/meal_mapper.py:58-76`.
- Domain-to-ORM mapping drops it at `src/infra/mappers/meal_mapper.py:202-221`.
- Meal updates delete and recreate all food-item rows through that mapper at `src/infra/repositories/meal_repository_async.py:538-555`, guaranteeing catalog-ID loss.
- Meal edit reconstructions preserve `fdc_id` but not catalog ID at `src/domain/strategies/meal_edit_strategies.py:88-105`, `src/domain/strategies/meal_edit_strategies.py:124-139`, and `src/domain/strategies/meal_edit_strategies.py:181-198`.
- The API response and request mapper expose `fdc_id`/allowed units but not catalog ID at `src/api/mappers/meal_mapper.py:168-182` and `src/api/mappers/meal_mapper.py:461-472`.
- Suggestion nutrition lookup finds and scales `food_reference_id`, but `src/domain/services/meal_suggestion/recipe_attempt_builder.py:128-156` never transfers it into suggestion ingredients. `src/app/handlers/command_handlers/meal_suggestion/save_meal_suggestion_command_handler.py:130-161` then creates custom `FoodItem`s without it.
- Existing mapper tests at `tests/unit/infra/test_meal_edit_database_models.py:194-267` assert only `fdc_id` and `is_custom`; preservation needs explicit round-trip and update tests.

No migration is needed merely to preserve the existing FK. A migration is needed only if recommendation/template persistence or new catalog classification fields are added.

## Existing Suggestions and Meal-Plan State

### Active suggestion flow

- `src/api/routes/v1/meal_suggestions.py:57-95` exposes AI discovery; `src/api/routes/v1/meal_suggestions.py:185-223` generates selected recipes; `src/api/routes/v1/meal_suggestions.py:226-277` saves a suggestion as a real meal.
- Discovery is AI-generated, session-based, and paginated, not deterministic/catalog-enumerated (`src/api/routes/v1/meal_suggestions.py:68-95`).
- `src/domain/model/meal_suggestion/suggestion_session.py:10-53` models a four-hour session. `src/infra/repositories/meal_suggestion_repository.py:19-93` stores it in required Redis transient state.
- The recipe path does calculate macros deterministically from ingredients, but still uses T2/T3 external/AI fallback and AI-created recipes (`src/domain/services/meal_suggestion/recipe_attempt_builder.py:34-105`). It is not a fully catalog-backed deterministic recommendation flow.
- Saved bookmarks are a separate normalized SQL feature at `src/api/routes/v1/saved_suggestions.py:17-66` and `src/infra/repositories/saved_suggestion_db_repository_async.py:26-128`; they are user-selected suggestions, not meal plans.

### Retired persistent meal plans and naming collisions

- `migrations/versions/025_drop_meal_plan_tables.py:21-25` explicitly dropped `planned_meals`, `meal_plan_days`, and `meal_plans`. Its downgrade at lines 28-88 is historical schema only.
- No active meal-plan ORM model, repository, CQRS handler, or route exists. `src/domain/model/meal_planning/meal_plan.py:11-115` and `src/domain/model/meal_planning/meal_generation_response.py:77-128` are surviving in-memory/legacy models.
- `src/domain/model/meal_planning/meal_suggestion.py:79-95` duplicates the active `src/domain/model/meal_suggestion/meal_suggestion.py:76-96` entity name with a different field set. Do not add another generic `MealSuggestion` or `MealPlan` without first choosing a bounded-context name.
- `src/domain/services/suggestion/suggestion_service.py:17-29` calls itself a meal recommendation service, but primarily chooses meal type/time, distributes calories, and filters already-created suggestions. It does not select catalog foods.
- `tests/unit/api/test_event_bus_dependency_singletons.py:97-150` still lists removed meal-plan handler names conditionally; because patching is guarded by `hasattr`, it does not prove those handlers are wired.

Recommended distinct naming: `MealRecommendationPlan`, `RecommendedDay`, `RecommendedMeal`, `GetThreeDayMealRecommendationsQuery`, and `/v1/meal-recommendations`.

## CQRS, UoW, and Production Registration

- The configured singleton composition root is `src/api/dependencies/event_bus.py:272-338`.
- Existing suggestion command registrations are at `src/api/dependencies/event_bus.py:547-561`; saved-suggestion registrations are at `src/api/dependencies/event_bus.py:715-729`.
- A new query requires imports in `src/api/dependencies/event_bus.py`, exports in the query/handler `__init__.py` files, and registration in `get_configured_event_bus()`.
- Routes are imported and mounted centrally at `src/api/main.py:52-68` and `src/api/main.py:308-334`.
- `AsyncUnitOfWorkPort` defines transaction ownership at `src/domain/ports/async_unit_of_work_port.py:21-62`; the concrete UoW commits/rolls back on context exit at `src/infra/database/uow_async.py:80-167`.
- Repositories must flush only; `src/infra/repositories/saved_suggestion_db_repository_async.py:26-96` is a compact model. Handlers should own `async with self.uow as uow`, as in `src/app/handlers/command_handlers/saved_suggestion/save_suggestion_command_handler.py:19-45`.
- `food_references` is still typed as `Any` at `src/domain/ports/async_unit_of_work_port.py:34-40`; no typed domain repository port exists. A new typed port would make the clean boundary explicit.

## Feature Flags and PostHog

- The existing DB flag model defaults off at `src/infra/database/models/feature_flag.py:11-20`; read/admin CRUD is exposed at `src/api/routes/v1/feature_flags.py:29-98` and `src/api/routes/v1/feature_flags.py:101-163`.
- DB flags are currently an API/config surface, not a handler-gating abstraction. No PostHog flag evaluation client exists.
- Default-off environment gates have a proven pattern at `src/infra/config/settings.py:268-288`, read lazily through API composition at `src/api/base_dependencies.py:185-199` and injected during event-bus construction at `src/api/dependencies/event_bus.py:339-358`.
- PostHog backend support is analytics only: LLM telemetry initializes at `src/api/main.py:180-205`; `src/infra/adapters/posthog_adapter.py:12-45` captures lifecycle events and fails open. It does not fetch/evaluate feature flags.

For MVP rollout, add a default-false setting such as `MEAL_RECOMMENDATIONS_ENABLED` and inject it at the route/handler composition boundary. If remote DB rollout is required, first add a typed read port/service; do not describe the current PostHog adapter as a feature-flag mechanism.

## Architecture Source Mismatches

- Current repository source of truth is PostgreSQL/asyncpg: `docs/database-guide.md:1-5`, `docs/system-architecture.md:38-46`, and `pyproject.toml` dependencies. The supplied project instruction block also contains an older MySQL statement; use the current docs/source.
- Historical `migrations/versions/035_evolve_barcode_to_food_reference.py:24-45` contains MySQL `DATABASE()` introspection despite the current PostgreSQL architecture. Do not copy that migration style; new migrations should follow current timestamped PostgreSQL migrations.
- The high-level instruction says commands do not return data, but current authoritative guide says commands return a domain entity or `None` at `docs/cqrs-guide.md:26-29`; `event_bus.send()` is synchronous at `docs/system-architecture.md:60-64`. A recommendation read is still clearly a query.
- `docs/system-architecture.md:52-69` requires ports and UoW ownership, but some existing query handlers directly import infra/UoW. New code should not extend that drift.

## Likely Implementation Surface

### Create

- `src/domain/model/meal_recommendation/` — specifically named response/domain value objects.
- `src/domain/services/meal_recommendation/` — pure deterministic selector/portion scaler; no SQLAlchemy, PostHog, or AI imports.
- `src/domain/ports/food_reference_repository_port.py` — typed catalog query projection/methods, if the broader UoW contract is cleaned up.
- `src/app/queries/meal_recommendation/get_three_day_meal_recommendations_query.py`.
- `src/app/handlers/query_handlers/get_three_day_meal_recommendations_query_handler.py`.
- `src/api/schemas/response/meal_recommendation_responses.py`.
- `src/api/routes/v1/meal_recommendations.py`.
- Focused unit/API/repository tests mirroring those paths.

### Modify

- `src/infra/repositories/food_reference_repository_async.py` — eligible catalog listing with explicit filters and stable order.
- `src/infra/repositories/food_reference_uow_adapter.py` and `src/domain/ports/async_unit_of_work_port.py` — only if that adapter/port participates.
- `src/api/dependencies/event_bus.py`, query/handler exports, and `src/api/main.py` — production wiring.
- `src/infra/config/settings.py` and a lazy settings helper — default-off rollout.
- `src/domain/model/nutrition/nutrition.py`, `src/infra/mappers/meal_mapper.py`, `src/domain/strategies/meal_edit_strategies.py`, suggestion ingredient mapping/save handler, and meal API schema/mapper — only when recommendations can be persisted/accepted as meals.
- `scripts/import_food_seeds.py` plus seed data/process — required before claiming reproducible catalog availability.

Avoid a new persistence migration for a response-only MVP. If plan history, acceptance state, or templates are required, design normalized user-owned tables per `docs/database-guide.md:10-21` rather than reviving the removed schema blindly.

## Test and Verification Commands

`uv` is unavailable in the current shell. The catalog scout verified this focused existing suite with `.venv/bin/python3.13`: **52 passed in 1.18s**.

```bash
.venv/bin/python3.13 -m pytest -q \
  tests/unit/infra/repositories/test_food_reference_projection.py \
  tests/unit/infra/repositories/test_food_reference_repository_async.py \
  tests/unit/infra/repositories/test_food_reference_batch.py \
  tests/unit/infra/repositories/test_food_reference_uow_adapter.py \
  tests/unit/infra/test_meal_edit_database_models.py \
  tests/migrations/test_food_payout_notification_normalization.py \
  tests/unit/domain/services/meal_suggestion/test_nutrition_lookup_service.py
```

Implementation verification should additionally run:

```bash
.venv/bin/python3.13 -m pytest -q \
  tests/unit/domain/services/meal_recommendation/ \
  tests/unit/app/handlers/test_three_day_meal_recommendations_query_handler.py \
  tests/unit/api/test_meal_recommendations_routes.py \
  tests/unit/api/test_event_bus_dependency_singletons.py \
  tests/migrations/test_alembic_revision_graph.py
.venv/bin/ruff check <touched-paths>
.venv/bin/python3.13 -m compileall src tests
.venv/bin/lint-imports
```

CI confirms `lint-imports` plus unit coverage are required at `.github/workflows/ci.yml:39-55`.

## Unresolved Questions

- Is production guaranteed to contain enough categorized, normalized, verified catalog rows for nine or more coherent meals?
- Is a deterministic 100g fallback acceptable when a catalog food has no usable serving row?
- Does MVP mean response-only recommendations, or must users accept/persist recommended meals?
- Should meal construction use algorithmic category slots, or should the product introduce curated meal templates/recipes?
- Is rollout controlled by deployment environment, the existing DB flags, or a future remote flag provider?

**Status:** DONE_WITH_CONCERNS

**Summary:** Exact catalog, serving, mapper, suggestion, meal-plan, CQRS, UoW, flag, migration, and test seams mapped. Existing primitives support a response-only deterministic MVP after adding stable catalog selection; saving recommendations also requires end-to-end `food_reference_id` preservation.

**Concerns/Blockers:** Catalog seed/import reproducibility is broken, catalog sufficiency is not verified, and `food_reference` lacks meal-template semantics. Product decisions remain for persistence, portion fallback, template strategy, and rollout source.
