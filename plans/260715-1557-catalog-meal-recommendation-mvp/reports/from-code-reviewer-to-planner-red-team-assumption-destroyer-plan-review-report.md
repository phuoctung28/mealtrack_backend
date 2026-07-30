# Red-Team Assumption Destroyer Plan Review

## Verdict

**BLOCKED before implementation.** The plan can complete every listed engineering step and still fail its MVP contract. Five assumptions below need explicit plan changes or verified product/data decisions. Findings intentionally exclude ordinary code-quality concerns.

## Findings

### 1. CRITICAL — The MVP requires a licensed three-cuisine recipe corpus, but the plan schedules only an importer

- **Plan location:** Phase 3, **Requirements** and **Implementation Steps** (`phase-03-immutable-curated-recipe-catalog.md:26-53`); overview success criterion (`plan.md:49-55`).
- **Unverified assumption:** At least 72 publishable recipe versions, covering Vietnamese/Japanese/Korean and every breakfast/lunch/dinner segment, already exist or can be acquired, normalized, nutrition-linked, image-cleared, and rights-cleared inside the 7-10 day phase.
- **Failure scenario:** Migration, domain, repository, and import code ship on time, but launch publication remains empty or Vietnamese-only. The `>=12` per cuisine/meal-type gate cannot pass, so generation always returns catalog insufficiency and the 5-7 week MVP misses delivery for a non-code dependency.
- **Codebase evidence:** The current importer recognizes Vietnamese-oriented sources only (`scripts/import_food_seeds.py:16-21`) and its fetch step downloads only NIN VN and OpenFoodFacts VN food data (`scripts/import_food_seeds.py:94-105`). Repository glob evidence found no version-controlled recipe corpus; `scripts/data/` contains only `meal_images_seed.csv`. Food composition rows are not curated recipes, instructions, source rights, or Japanese/Korean coverage.
- **Required correction:** Add a gated data workstream with corpus owner, exact source/license, committed artifact path, cuisine/segment counts, image rights, ingredient-link acceptance rate, and a pre-Phase-3 sample dry-run. Re-estimate after that evidence exists.

### 2. HIGH — “Immutable recipe version” is not reproducible while its nutrition authority is mutable

- **Plan location:** Phase 3, **Architecture** and steps 3-5 (`phase-03-immutable-curated-recipe-catalog.md:31-53`); Phase 6, logging step (`phase-06-transactional-swap-and-meal-logging.md:44-51`).
- **Unverified assumption:** Referencing `food_reference` plus storing recipe totals is enough to reproduce every ingredient's macros later when logging a plan.
- **Failure scenario:** Recipe version V1 is published from ingredient reference R at 20 g protein/100 g. A later barcode/name upsert corrects R to 25 g. The plan still points to V1, but logging materializes ingredient macros from current R; the ordinary meal no longer matches V1's stored total. The same immutable version now yields different nutrition across time and existing plans become internally inconsistent.
- **Codebase evidence:** `food_reference` is explicitly mutable and carries `updated_at` with `onupdate` (`src/infra/database/models/food_reference_model.py:38-59`). Current upserts replace macro, serving, density, and source fields on conflict (`src/infra/repositories/food_reference_repository_async.py:80-120`, `174-195`). The plan names recipe totals and FKs but never requires per-version ingredient snapshots of resolved grams, per-ingredient macros, conversion inputs, and source revision.
- **Required correction:** Define the immutable snapshot boundary. Each published recipe ingredient must persist resolved grams and the macro/conversion values used at publication; logging must materialize only from that snapshot. Keep `food_reference_id` as lineage, not as a future nutrition lookup.

### 3. HIGH — The promised 90-day affinity has no reliable production history input

- **Plan location:** Phase 2, steps 1-2 (`phase-02-canonical-ingredient-and-nutrition-foundation.md:45-51`); Phase 4, **Requirements** (`phase-04-deterministic-recommendation-domain.md:26-29`); Phase 5, step 3 (`phase-05-durable-plans-cqrs-and-api.md:47-54`).
- **Unverified assumption:** Repairing canonical-ID round trips prospectively makes 90 days of linked history available and the existing range query is suitable for recency scoring.
- **Failure scenario:** An established user launches on day one. Prior meals have IDs dropped by current domain/mappers, and no backfill is planned, so the “linked-history” profile is empty. For a heavy logger with more than 500 meals in 90 days, the generic query returns the oldest 500 and silently excludes the newest meals, inverting a recency-weighted affinity signal.
- **Codebase evidence:** `FoodItem` currently has no `food_reference_id` field (`src/domain/model/nutrition/nutrition.py:10-24`); ORM-to-domain drops the existing FK (`src/infra/mappers/meal_mapper.py:60-76`), and domain-to-ORM does not write it (`src/infra/mappers/meal_mapper.py:202-212`). The only existing date-range history method defaults to 500 rows, orders ascending, then limits (`src/infra/repositories/meal_repository_async.py:375-405`). Phase 2 specifies no historical backfill, while Phase 5 specifies no dedicated bounded history projection/query.
- **Required correction:** Decide product truth: cold-start all existing users, or backfill canonical links with a measurable confidence policy. Add a dedicated owner-scoped 90-day projection that selects only needed linked ingredients, orders for recency semantics, and has an explicit volume policy; test >500 meals.

### 4. HIGH — A singular “profile target” cannot represent the current date-dependent nutrition contract for a 3-day plan

- **Plan location:** Phase 1, target/start-date decision (`phase-01-contract-and-regression-lock.md:43-49`); Phase 4, three-date requirements (`phase-04-deterministic-recommendation-domain.md:26-33`); Phase 5, snapshot/handler design (`phase-05-durable-plans-cqrs-and-api.md:31-54`).
- **Unverified assumption:** One snapshotted target resolved from the profile is the correct calorie target for all three plan dates.
- **Failure scenario:** A plan starts Sunday. Sunday's target is adjusted from the closing weekly budget, while Monday starts a new weekly budget; movement, logged meals, cheat days, and remaining days can also change the effective target by date. Persisting one target causes at least one day's recommendations and deviation metrics to disagree with the application's nutrition source of truth.
- **Codebase evidence:** `WeeklyBudgetService` declares itself the single source of truth for adjusted daily targets (`src/domain/services/weekly_budget_service.py:1-7`). Its contract explicitly requires `week_start` and `target_date` (`src/domain/services/weekly_budget_service.py:238-269`) and derives remaining days, prior logging, consumption, and per-day adjustment (`src/domain/services/weekly_budget_service.py:282-320`, `343-420`). The current suggestion helper resolves only `today` and that week's budget (`src/domain/services/meal_suggestion/suggestion_tdee_helpers.py:50-93`), so it cannot simply be reused for arbitrary three-day starts.
- **Required correction:** Specify whether targets are a three-element per-date snapshot or a deliberately fixed planning target. If aligned with current behavior, resolve each local date against the correct weekly budget, including week crossings, custom macros, movement/cheat semantics, and a documented future-date rule.

### 5. HIGH — Controlled cohort rollout and raw view measurement have no executable control/API contract

- **Plan location:** Phase 1, contract/event ownership (`phase-01-contract-and-regression-lock.md:28-49`); Phase 7, **Requirements**, **Architecture**, and steps 1-2/6 (`phase-07-measurement-and-controlled-rollout.md:27-52`).
- **Unverified assumption:** A process-wide environment boolean plus an optional existing DB boolean can support “internal accounts, then small cohort,” and client-owned view events can be persisted without a new request contract.
- **Failure scenario:** Operations sets `MEAL_RECOMMENDATIONS_ENABLED=true` to test internal users. Every authenticated user can call create/swap/log because neither gate represents identity/cohort membership. Separately, the client displays plans and alternatives, but there is no planned ingestion endpoint/command/schema for `plan_viewed` or `alternative_viewed`; conversion denominators stay zero or are inferred incorrectly, so expansion decisions are invalid.
- **Codebase evidence:** The existing feature-flag model contains only global `name` and `enabled` (`src/infra/database/models/feature_flag.py:11-20`), and its reads return the same boolean dictionary without user context (`src/api/routes/v1/feature_flags.py:32-57`, `60-98`). PostHog is outbound capture only (`src/infra/adapters/posthog_adapter.py:23-45`). Repository search found no interaction/view-event ingestion path. Phase 7's related files do not create a route, request schema, command, cohort evaluator, membership store, or deterministic bucketing policy (`phase-07-measurement-and-controlled-rollout.md:36-43`).
- **Required correction:** Freeze a user-scoped evaluator contract before schema work: hard kill switch AND explicit internal allowlist/deterministic cohort mechanism, with precedence and outage behavior. Add authenticated, owner-scoped, deduplicated interaction ingestion API/command schemas and consumer contract tests, or remove client-view metrics from MVP success decisions.

## Scope Audit

- These are plan blockers, not requests for ranking sophistication, Redis, AI, popularity learning, or undo.
- Fixing them narrows uncertainty: prove the catalog, freeze snapshot semantics, define real history/targets, and make rollout measurable.
- Do not begin migrations until findings 1, 2, 4, and 5 are resolved in Phase 1 gates; finding 3 needs an explicit product choice and query/backfill task.

## Unresolved Questions

1. Who owns and licenses the initial recipe corpus, and where is the representative artifact?
2. Is food-reference nutrition revisioned, or must recipe versions snapshot every ingredient nutrition input?
3. Is day-one affinity expected for existing users, or is documented cold start acceptable?
4. Should three-day targets be fixed at generation or date-specific under weekly redistribution?
5. What exact server-side cohort mechanism and client interaction endpoint will be used?

**Status:** DONE_WITH_CONCERNS  
**Summary:** Reviewed all eight plan documents and traced the five strongest assumptions to current catalog, food-reference, meal-history, nutrition-target, feature-flag, and analytics paths.  
**Concerns/Blockers:** Plan remains implementation-blocked until the five findings above are dispositioned.
