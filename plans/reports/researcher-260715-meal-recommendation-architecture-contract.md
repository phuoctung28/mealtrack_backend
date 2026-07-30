---
title: Meal Recommendation MVP Architecture Contract Analysis
type: researcher-report
status: complete
created: 2026-07-15
sources:
  - /Users/alexnguyen/Downloads/nutree_meal_recommendation_mvp_architecture.md
  - plans/research/260715-1547-catalog-meal-recommendation-foundation.md
---

# Meal Recommendation MVP Architecture Contract Analysis

## Summary

Both documents agree on a new catalog-backed, deterministic 3-day meal-plan feature beside the existing AI suggestion flow. The repository research should control where it reflects verified current-state constraints: reuse `food_reference`, preserve `food_reference_id`, derive calories from macros, version recipes immutably, and defer popularity learning, Redis recommendation caching, and undo. The supplied architecture remains useful for plan shape, deterministic selection, durability, concurrency, source rights, CQRS boundaries, and failure contracts, but its schema and rollout phases require reconciliation before implementation.

## Source Priority

1. **Repository research** — verified repository fit and approved direction (`Current-State Findings`, `Recommended Architecture`, `Explicit Non-Goals for MVP`).
2. **Architecture draft** — detailed proposed design where it does not contradict repository findings (`Executive decisions`, `Architectural fit`, `MVP acceptance checklist`).
3. **Implementation plan** — must explicitly resolve conflicts below; it must not silently merge both models.

## Locked Product Decisions

| Decision | Contract | Source sections |
|---|---|---|
| Feature boundary | New catalog-backed meal-plan feature; existing `/v1/meal-suggestions` stays unchanged. | Architecture: `Executive decisions`, `Migration and rollout plan`; research: `Current-State Findings`, `Explicit Non-Goals for MVP` |
| Runtime behavior | No runtime LLM, live recipe lookup, scraping, embeddings, vector search, or graph database. | Architecture: `Executive decisions`, `Explicit MVP exclusions`; research: `Explicit Non-Goals for MVP` |
| Plan shape | 3 consecutive days; breakfast, lunch, dinner each day; 9 slots total. | Architecture: `Executive decisions`, `Nine-slot plan optimization`, `MVP acceptance checklist`; research: `Research Scope` |
| Alternatives | Five deterministic alternatives per slot, generated from the same eligible catalog snapshot. | Architecture: `Alternative generation`; research: `Research Scope`, `Durable Recommendation Plans` |
| Cuisines | Vietnamese, Japanese, Korean only for MVP. | Architecture: `Executive decisions`, `Hard constraints`; research: `Research Scope` |
| Calories | Backend source of truth; daily target divided equally by 3. Recipe calories must ultimately be derived from resolved macros. | Architecture: `Calorie-target policy`; research: `Versioned Recipe Catalog`, `Success Criteria` |
| Catalog | Curated, version-controlled internal catalog; no recipes currently exist; publication requires validation and provenance. | Architecture: `Catalog seed design`, `Security, privacy, and content safety`; research: `Current-State Findings`, `Build the Curated Recipe Catalog` |
| Durability | PostgreSQL is authoritative. Plans, slots, selected recipe versions, alternatives, swaps, and source interactions are durable. | Architecture: `Architectural fit`, `Meal Plan`, `Unit of Work integration`; research: `Durable Recommendation Plans` |
| Personalization | Deterministic ingredient-history affinity only when canonical linked history exists; cold start must remain deterministic and catalog-quality-driven for first launch. | Architecture: `Existing-user ingredient profile`; research: `Implement Deterministic Recommendation Logic`, `Explicit Non-Goals for MVP` |
| Swap | One owned durable slot changes transactionally; other eight stay unchanged; idempotency and optimistic concurrency required. | Architecture: `Meal Plan`, `Swap architecture`, `MVP acceptance checklist`; research: `Persist Plans and Alternatives` |
| Allergy contract | No allergy filtering or safety claim. API must explicitly communicate that allergies were not evaluated. | Architecture: `Executive decisions`, `Security, privacy, and content safety`; research: `Add API, CQRS, and Normal Meal Logging` |
| Logging | A selected recipe can be logged through the normal meal flow with immutable nutrition snapshots and canonical ingredient identity preserved. | Research: `Logging and Measurement`, `Success Criteria` |
| Rollout | Default off; controlled internal/cohort rollout; raw events retained for future ranking. | Architecture: `Controlled rollout`, `Feature flags and algorithm versioning`; research: `Add Rollout and Observability` |

## Schema and Domain Invariants

### Ingredient and Nutrition

- `food_reference` is the sole canonical nutritional identity; do not add the architecture draft's standalone `ingredients` authority. Recipe ingredients reference canonical foods and may have aliases (`One Ingredient Authority`).
- Preserve `food_reference_id` end to end across ORM, domain, mapper, API, and normal meal logging (`Current-State Findings`, `Logging and Measurement`).
- Every nutritionally meaningful published ingredient resolves quantity/unit to grams through food-specific serving conversions. Unknown or ambiguous conversions fail publication; never assume grams (`One Ingredient Authority`).
- Display-only ingredients are allowed only when explicitly marked and excluded from nutrition (`One Ingredient Authority`).
- Calories follow the repository invariant and are derived from resolved macros; source calories can be validation input, not the authoritative value (`Versioned Recipe Catalog`).

### Recipe Catalog

- Separate stable recipe identity from immutable published recipe versions. A version owns cuisine, meal types, servings, instructions, ingredients, provenance, computed nutrition, and publication state (`Versioned Recipe Catalog`).
- Plans and logged meals reference/snapshot a specific published version, never mutable latest recipe data (`Durable Recommendation Plans`).
- Provenance, source URL, rights, attribution, and hosting permission are required before publication/display (`Recipe details`, `Security, privacy, and content safety`).
- Seed/import is idempotent, dry-runnable, validates coverage, and never auto-deletes absent records (`Catalog seed design`).

### Plan and Recommendation

- Exactly 9 unique slot identities across 3 consecutive local dates; one breakfast/lunch/dinner per date (`Nine-slot plan optimization`).
- Current plan contains no duplicate recipe/version selection; only published, nutritionally valid, supported-cuisine recipes eligible for the requested meal type (`Hard constraints`, `Result validation`).
- Snapshot timezone, resolved daily target, slot target, catalog/algorithm version, and ranking components needed for reproducibility (`Durable Recommendation Plans`, `Recommendation score`).
- Five unique alternatives per slot; alternatives cannot duplicate the current nine and are not impressions until returned to the user (`Alternative generation`).
- If fewer than 9 unique eligible recipes remain after documented tolerance fallback, return typed catalog-insufficient failure; never duplicate silently (`Failure and fallback policy`).
- Ranking and exploration, if any, use stable tie-breaking/seed so retries reproduce the same result (`Exploration`, `Implement Deterministic Recommendation Logic`).

### Persistence, Concurrency, and Security

- Commands write, queries read; domain imports no FastAPI, SQLAlchemy, Redis, application handlers, or infrastructure (`Architectural fit`).
- `AsyncUnitOfWork` owns commit/rollback; repositories flush only; critical swaps/interactions persist within the command transaction (`Unit of Work integration`, `CQRS mapping`).
- Create and swap have durable idempotency keys; slot swap uses ownership-scoped row locking plus expected slot version; stale writes return 409 (`Swap architecture`, `Failure and fallback policy`).
- Every plan/slot/swap/interaction query is scoped by authenticated user; cross-user lookup must not reveal existence (`Security, privacy, and content safety`).
- Redis must never be required for correctness. For MVP planning, omit recommendation caches entirely unless later measurement justifies them (`Explicit Non-Goals for MVP`).

## API Contract Baseline

Retain these endpoints from architecture `API design`, adjusted for recipe versions and the explicit allergy contract:

- `POST /v1/meal-plans/three-day` — authenticated, idempotent creation; profile-derived daily target unless validated override.
- `GET /v1/meal-plans/{plan_id}` — owner-scoped durable read.
- `POST /v1/meal-plans/{plan_id}/slots/{slot_id}/swap` — request ID plus expected slot version; returns updated slot/day totals.
- `GET /v1/recipes/{recipe_id}` or version-aware equivalent — response constrained by content rights.
- Normal meal-create/logging flow — accepts a selected recipe version and materializes ordinary meal food items with immutable nutrition and `food_reference_id`.

Required response semantics:

- `allergy_evaluated: false`; do not merely hide an empty allergen list.
- Recipe/version ID, slot version, plan version, source attribution, calories/macros, and `can_swap` are explicit.
- Cross-user plan access maps to not-found behavior.
- Catalog insufficiency is typed; stale slot version is 409; duplicate retries return the committed result.

Do not include undo or client-authored `shown` impressions in the first MVP API. Server owns exposure events (`Interaction capture`; research `Explicit Non-Goals for MVP`).

## Contradictions Requiring Resolution

| Topic | Architecture draft | Repository research | Recommended resolution |
|---|---|---|---|
| Ingredient authority | New `ingredients` and `ingredient_aliases` tables (`PostgreSQL schema`). | `food_reference` must remain sole authority (`One Ingredient Authority`). | Replace draft ingredient tables with recipe-to-`food_reference` links plus existing/extended alias and serving conversion paths. |
| Recipe mutability | Single mutable `recipes` row holds nutrition/content (`Catalog tables`). | Stable recipe plus immutable published versions (`Versioned Recipe Catalog`). | Add recipe-version model; plan slots reference version IDs. |
| Calorie authority | Stores supplied `calories_per_serving` beside macros (`Recipe aggregate`). | Derive calories from resolved macros (`Versioned Recipe Catalog`). | Compute authoritative macros/calories at publish time; snapshot version nutrition. |
| Popularity MVP scope | Interaction weights, Bayesian score table, exploration, cron, and dedicated PR (`New-user popularity`, `Popularity aggregate cron`, `Migration and rollout plan`). | Learned popularity, exploration, ranking cron deferred until interaction volume (`Explicit Non-Goals for MVP`). | Store raw events now; use deterministic quality/nutrition/diversity cold-start ranking. Defer aggregate tables/cron/learned exploration. |
| Redis | Ingredient/popularity caches designed into MVP (`Caching strategy`). | No Redis recommendation cache initially (`Explicit Non-Goals for MVP`). | Exclude cache code and keys from first implementation; PostgreSQL correctness only. |
| Undo | Endpoint, domain command, audit behavior, tests, PR 5 (`Undo`, `CQRS mapping`). | No undo workflow (`Explicit Non-Goals for MVP`). | Defer undo endpoint/command/tests; retain swap audit schema sufficient for later addition. |
| Completion/cooked state | `cooked` interactions and optional complete-plan command (`Interaction and Popularity`, `CQRS mapping`). | Log through normal meal flow; no separate cooked/completed state (`Logging and Measurement`, `Explicit Non-Goals for MVP`). | Treat successful normal meal logging as the conversion event; omit separate completion state. |
| Interaction vocabulary | shown/opened/saved/cooked/swapped events (`Interaction and Popularity`). | plan viewed/alternative viewed/swap selected/meal logged (`Logging and Measurement`). | Lock a single raw event enum and server/client ownership before migration; favor product-observable events from research. |
| Aggregate name | Generic `MealPlan` (`Meal plan aggregate`). | `CatalogMealPlan` avoids collision with existing AI planning (`Durable Recommendation Plans`). | Use catalog-specific domain/ORM naming while API may remain `/meal-plans`. |
| Allergy representation | Internal empty exclusion collection (`Executive decisions`). | Explicit `allergy_evaluated: false` API (`Add API, CQRS, and Normal Meal Logging`). | Keep empty internal filter and expose explicit false response field. |
| Catalog launch threshold | Target 180–270 recipes; no minimum launch gate (`Catalog seed design`). | At least 12 per cuisine × meal-type segment and 72 unique published (`Build the Curated Recipe Catalog`). | Treat 180–270 as long-run target; enforce 12/segment and 72 unique as controlled-launch minimum. |
| Plan lifecycle | active/completed/superseded statuses, but regeneration behavior unspecified (`Plan tables`). | Regeneration disposition unresolved (`Unresolved Questions`). | Do not finalize status/index/API semantics until product chooses replacement vs retained revision. |

## MVP Boundaries

### In MVP

- Ingredient identity/conversion repair, immutable versioned catalog, validated seed/import.
- 3-day deterministic plan, five alternatives per slot, durable reads, transactional swap.
- Existing-user affinity only from canonical linked history; deterministic cold-start scoring.
- Normal meal logging with macro snapshots and canonical identity.
- Raw product interactions, bounded observability, boolean backend gate plus controlled exposure.
- Unit, repository, API, architecture, concurrency, and catalog validation tests.

### Deferred / Non-Goals

- Existing AI-suggestion replacement, runtime AI, external lookup, scraping, automated ingestion.
- Learned popularity, Bayesian aggregate cron, exploration algorithms, Redis recommendation cache.
- Undo, separate cooked/completed workflow, allergies/health-condition filtering.
- Embeddings, pgvector recommendation, collaborative/user-neighbor models, graph database.
- Seven-day plans, grocery/budget optimization, social/creator features, mobile implementation.

## Recommended Phase Decomposition

### Phase 1 — Contract and Regression Lock

- Finalize recipe-version, plan lifecycle, raw event enum, API payloads, calorie/timezone/idempotency rules.
- Protect existing `/v1/meal-suggestions` and normal meal logging with regression tests.
- Exit: contradictions above resolved in plan; no migration yet.

### Phase 2 — Canonical Ingredient and Nutrition Foundation

- Preserve `food_reference_id` through all existing boundaries.
- Implement alias resolution and strict food-specific quantity-to-gram conversion.
- Test backend macro-derived calories, ambiguity rejection, display-only ingredients.
- Exit: canonical ingredient and normal meal paths verified.

### Phase 3 — Immutable Curated Catalog

- Migrate recipe identity/version/ingredient/source/meal-type schema.
- Add domain models, mappers, repository/UoW registration, validator, idempotent seed/import, rights checks.
- Gate publishing and launch coverage: 12 eligible recipes per cuisine/meal-type segment and 72 unique; 180–270 remains target.
- Exit: published version reproducible and catalog release gate passes.

### Phase 4 — Pure Deterministic Recommendation Domain

- Implement calorie policy, canonical history affinity, quality/calorie/diversity scoring, 9-slot optimizer, alternatives, stable tie-breaking.
- Add golden/property tests for invariants and insufficient-catalog fallback.
- Exit: no DB/API dependency in domain; same input produces same result.

### Phase 5 — Durable Plans, CQRS, and Read/Create API

- Migrate catalog-plan/slot/alternative tables referencing recipe versions.
- Implement owner-scoped repositories, idempotent create, command/query handlers, schemas, mappers, routes, composition registration.
- Persist full 9-slot aggregate and alternatives atomically.
- Exit: create/read API integration tests pass without Redis/external calls.

### Phase 6 — Transactional Swap and Normal Meal Logging

- Add swap audit, row locking, optimistic version checks, deterministic alternative fallback, retry replay.
- Convert selected recipe version to ordinary meal food items with immutable macro snapshots and `food_reference_id`.
- Exit: concurrent swap, retry, ownership, and logging integration tests pass; only one slot changes.

### Phase 7 — Raw Measurement and Controlled Rollout

- Add agreed raw events and bounded metrics/logs; server records exposures.
- Default feature off; use boolean backend gate and existing cohort mechanism only after its control path is confirmed.
- Run architecture tests, migration-head checks, catalog validation, latency checks, and internal cohort rollout.
- Exit: controlled-launch checklist passes; existing AI flow remains available.

### Post-MVP Phase

- After sufficient interaction volume: popularity aggregate/read model, Bayesian ranking, exploration, measured caching.
- Later: undo, allergy completeness/filtering, automated ingestion, semantic/collaborative ranking, longer plans.

## Main Risks

| Risk | Impact | Mitigation / phase gate |
|---|---|---|
| Parallel ingredient authority | Split nutrition identity and unusable history affinity. | Phase 2 blocks catalog work until `food_reference` contract is proven. |
| Mutable recipes | Old plans/logged meals change meaning. | Immutable published versions and version IDs in Phase 3. |
| Bad unit conversion | Incorrect macros/calories; health trust loss. | Publish-time strict conversion and macro-derived calorie tests. |
| Catalog coverage too thin | Incomplete or repetitive plans; swap exhaustion. | Segment/unique launch gates plus typed insufficiency failure. |
| Premature popularity complexity | Unvalidated ranking and operational cron/cache burden. | Raw events only; promote learned ranking after measured volume. |
| Concurrency/idempotency defects | Duplicate plans or overwritten swaps. | DB constraints, owner-scoped locking, expected versions, retry tests. |
| Feature contract collision | Existing AI suggestion or meal logging regression. | Separate catalog naming/routes and Phase 1 regression lock. |
| Rights/allergy overclaim | Legal or user-safety exposure. | Provenance/publishing gate and explicit `allergy_evaluated: false`. |
| Scope creep from detailed draft | Undo/cache/popularity delay core validation. | Enforce MVP boundary table at each phase review. |

## Unresolved Questions

1. Initial recipe content source and license/hosting rights?
2. Seed files only for initial publishing, or an admin workflow?
3. Regeneration: supersede the active plan, retain a revision, or reject while one is active?
4. Exact raw interaction enum and which events are server-owned versus client-submitted?
5. Valid product limits for explicit daily-calorie override and allowed plan `start_date` window?
6. Exact existing cohort mechanism: PostHog exposure only, or a backend-evaluated percentage gate?

**Status:** DONE
**Summary:** Reconciled the architecture draft with repository research, extracted implementation contracts, and proposed seven MVP phases that prioritize canonical ingredient/nutrition correctness before recommendation and rollout.
**Concerns/Blockers:** Ingredient authority, recipe versioning, plan regeneration lifecycle, and interaction taxonomy must be explicitly locked before schema implementation; learned popularity, Redis caching, and undo should remain post-MVP.
