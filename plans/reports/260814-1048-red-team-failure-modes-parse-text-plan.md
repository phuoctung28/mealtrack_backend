# Parse-Text Plan Red-Team Failure Modes

Scope reviewed:
- `plans/260814-1035-parse-text-fatsecret-validation-harness/plan.md`
- `plans/260814-1035-parse-text-fatsecret-validation-harness/phase-01-characterize-parse-text-nutrition-contracts.md`
- `plans/260814-1035-parse-text-fatsecret-validation-harness/phase-02-implement-structured-reference-resolution.md`
- `plans/260814-1035-parse-text-fatsecret-validation-harness/phase-03-build-evaluation-harness-and-release-gates.md`

Sticky boundaries verified:
- Same authenticated + guest public response contract is shared through one command path: `src/api/routes/v1/meals_manual_text.py:141-180`, `src/api/routes/v1/meals_manual_text.py:185-258`, `src/api/dependencies/event_bus.py:505-513`
- Parse-text already has one whole-payload schema retry and controlled `AI_OUTPUT_INVALID` mapping: `src/app/handlers/command_handlers/parse_meal_text_handler.py:143-188`, `src/api/exceptions.py:136-160`
- Backend calories are derived from macros, not trusted totals: `src/app/handlers/command_handlers/parse_meal_text_handler.py:231-237`

## Findings

### 1. High — Request timeout budget is still unowned across item fan-out

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:109-124`

Verified live code:
- Parse-text can return up to 20 items: `src/domain/model/ai/nutrition_contracts.py:283-288`
- Handler resolves items sequentially: `src/app/handlers/command_handlers/parse_meal_text_handler.py:90-95`
- Each item gets its own FatSecret timeout, default 3 seconds: `src/app/handlers/command_handlers/parse_meal_text_handler.py:43-45`, `src/app/handlers/command_handlers/parse_meal_text_handler.py:268-270`
- Current `search_foods()` already expands one search into per-hit detail fetches: `src/infra/adapters/fat_secret_service.py:198-228`

Affected callers:
- `POST /v1/meals/parse-text` -> `event_bus.send(ParseMealTextCommand)` at `src/api/routes/v1/meals_manual_text.py:141-180`
- `POST /v1/meals/parse-text/guest-trial` -> same command at `src/api/routes/v1/meals_manual_text.py:185-258`
- shared handler registration at `src/api/dependencies/event_bus.py:505-513`

Failure mode:
- A 20-item payload can still spend N x timeout before any semantic retry logic runs. The plan says "one bounded timeout budget" but does not assign a request-level deadline, cancellation rule, or concurrency cap. That is an approval gap, not an implementation detail.

### 2. High — “Reuse NutritionResolver” hides a net-new production seam

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:36-38`, `phase-02-implement-structured-reference-resolution.md:76-78`

Verified live code:
- `NutritionResolver` only exact-matches a preloaded local dict and scales macros: `src/domain/services/nutrition_resolver.py:33-68`
- It has no provider search, tie handling, candidate scoring, completeness validation, or retry interface: `src/domain/services/nutrition_resolver.py:41-68`
- Current production parse-text logic does all lookup/orchestration inside the handler: `src/app/handlers/command_handlers/parse_meal_text_handler.py:242-310`

Affected callers:
- Any production introduction of `NutritionResolver` changes the same two parse-text routes at `src/api/routes/v1/meals_manual_text.py:141-180`, `src/api/routes/v1/meals_manual_text.py:185-258`
- shared construction path at `src/api/dependencies/event_bus.py:505-513`

Failure mode:
- Phase 2 is described like an extension of an existing resolver, but the live resolver is a test-scale local matcher. Approving the phase as a “refactor” understates scope, rollback cost, and required composition-root changes.

### 3. High — Shared FatSecret caller blast radius is not enumerated

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:33-40`, `phase-02-implement-structured-reference-resolution.md:109-117`, `phase-02-implement-structured-reference-resolution.md:164-165`

Verified live code:
- Parse-text currently calls `FatSecretService.search_foods()` directly: `src/app/handlers/command_handlers/parse_meal_text_handler.py:268-270`
- Other live callers also rely on `search_foods()`:
  - `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py:55`
  - `src/app/handlers/query_handlers/search_foods_query_handler.py:94`
  - `src/app/handlers/query_handlers/search_foods_query_handler.py:135`
  - `src/app/handlers/query_handlers/search_foods_query_handler.py:154`
  - `src/app/handlers/query_handlers/search_foods_query_handler.py:181`
  - `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:250`
- Shared service behavior today is search -> fetch details for each candidate: `src/infra/adapters/fat_secret_service.py:189-228`

Affected callers:
- parse-text routes
- food search query handler callers
- barcode lookup caller
- meal-suggestion `IngredientNutritionResolver`

Failure mode:
- If the staged-provider change is implemented by mutating shared `search_foods()` semantics instead of isolating parse-text to `search_food_candidates()/get_food_details()`, unrelated endpoints change behavior or latency. The plan says “do not change `IngredientNutritionResolver` or `NutritionLookupService` behavior” but does not lock that isolation with caller enumeration or rollback steps.

### 4. High — The planned validator asks for fields the live FatSecret detail shape does not provide

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:48-63`

Verified live code:
- Structured FatSecret detail extraction returns only calories/protein/carbs/fat plus serving text and allowed units: `src/infra/adapters/fat_secret_service.py:345-366`
- Search results stamp `source="fatsecret"` and default `allowed_units` before real detail enrichment: `src/infra/adapters/fat_secret_service.py:418-429`
- Legacy parse-text still parses nutrition from `food_description` text: `src/app/handlers/command_handlers/meal_text_parsing_utils.py:93-124`, `src/app/handlers/command_handlers/parse_meal_text_handler.py:273-304`

Affected callers:
- parse-text handler path at `src/app/handlers/command_handlers/parse_meal_text_handler.py:268-304`
- meal-analyze reference-validation provider path through `FatSecretNutritionReferenceProvider.get_food_details()` at `src/infra/adapters/fatsecret_nutrition_reference_provider.py:28-34`

Failure mode:
- The phase requires `fiber <= carbs`, `sugar <= carbs`, completeness, and provider-energy checks, but live structured details do not carry fiber or sugar. Either many valid details will be rejected as incomplete, or the plan’s “complete records only” rule is not actually implementable on the current provider shape.

### 5. High — Semantic retry scope is undefined and can multiply whole-request AI calls

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:59-63`, `phase-02-implement-structured-reference-resolution.md:118-124`

Verified live code:
- Current parse-text already retries the whole payload once on schema validation: `src/app/handlers/command_handlers/parse_meal_text_handler.py:40`, `src/app/handlers/command_handlers/parse_meal_text_handler.py:143-188`
- Provider resolution happens after that, inside the per-item loop: `src/app/handlers/command_handlers/parse_meal_text_handler.py:90-95`, `src/app/handlers/command_handlers/parse_meal_text_handler.py:242-310`

Affected callers:
- `POST /v1/meals/parse-text` at `src/api/routes/v1/meals_manual_text.py:141-180`
- `POST /v1/meals/parse-text/guest-trial` at `src/api/routes/v1/meals_manual_text.py:185-258`

Failure mode:
- The plan adds “one semantic AI retry” for unresolved reference cases but never states whether that retry is per request or per unresolved item. Per-item retry explodes cost/latency. Per-request retry needs a defined merge contract for partially resolved items. The phase cannot be approved until that unit of retry is explicit.

### 6. Medium — Phase 1 characterization asks for seams that do not exist yet

Plan claim:
- `phase-01-characterize-parse-text-nutrition-contracts.md:43-46`, `phase-01-characterize-parse-text-nutrition-contracts.md:79-91`

Verified live code:
- Live handler never calls `get_food_details()` directly; it only calls `search_foods()`: `src/app/handlers/command_handlers/parse_meal_text_handler.py:268-270`
- Existing parse-text tests are shaped around fake `search_foods()` services and monkeypatched legacy parser helpers:
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:50`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:55`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:61`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:144`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:145`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:292`
  - `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:293`

Affected callers:
- parse-text handler test slice
- route compatibility checks for both public parse-text endpoints

Failure mode:
- Phase 1 says to characterize “exactly one selected detail request” before runtime changes, but the live runtime has no direct detail-call seam to characterize. That pushes the team toward future-seam mocks in a supposedly current-state TDD phase.

### 7. Medium — Rollback is missing at the shared event-bus boundary

Plan claim:
- `phase-02-implement-structured-reference-resolution.md:107-117`

Verified live code:
- Both authenticated and guest parse-text routes depend on the same `get_configured_event_bus()` path: `src/api/routes/v1/meals_manual_text.py:147-168`, `src/api/routes/v1/meals_manual_text.py:191-192`, `src/api/routes/v1/meals_manual_text.py:232-242`
- `ParseMealTextHandler` is registered once in the shared composition root: `src/api/dependencies/event_bus.py:505-513`

Affected callers:
- `POST /v1/meals/parse-text`
- `POST /v1/meals/parse-text/guest-trial`

Failure mode:
- A bad constructor change, provider seam, or timeout object breaks both endpoints at once. The plan names one singleton wiring test file, but not a feature flag, default-off constructor arg, or rollback switch at the composition root.

### 8. Medium — Offline/live evaluation can diverge on timeout behavior even if logic matches

Plan claim:
- `phase-03-build-evaluation-harness-and-release-gates.md:41-50`, `phase-03-build-evaluation-harness-and-release-gates.md:91-107`

Verified live code:
- Parse-text request timeout is an env-based 3-second guard by default: `src/app/handlers/command_handlers/parse_meal_text_handler.py:43-45`
- Shared FatSecret transport timeout is 30 seconds: `src/infra/adapters/fat_secret_service.py:48-52`

Affected callers:
- both parse-text routes through the same live handler path

Failure mode:
- The harness phase talks about offline gates plus live latency evidence, but it does not bind evaluation to the same timeout-budget object as production. Offline fakes can pass while live staging still runs under different timeout layering and percentiles.

## Recommendation

Do not approve Phase 2 as written yet.

Approval conditions:
1. Name the request-level timeout/cancellation/concurrency policy for multi-item parse-text.
2. Decide whether Phase 2 introduces a new parse-text resolver seam or truly extends an existing production service.
3. Lock isolation from shared `FatSecretService.search_foods()` callers.
4. Freeze the accepted structured FatSecret detail contract before writing completeness rules.
5. Specify semantic retry unit: per request only, or per item with a hard cap.
6. Add a composition-root rollback switch or default-off wiring change.

## Unresolved Questions

None.

**Status:** DONE_WITH_CONCERNS
**Summary:** Plan direction is viable, but the live code shows eight approval gaps around fan-out latency, shared caller blast radius, provider-shape mismatch, retry scope, and rollback isolation.
**Concerns/Blockers:** Phase 2 should not start until the approval conditions above are resolved.
