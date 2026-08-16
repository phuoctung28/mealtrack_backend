---
phase: 2
title: "Implement Structured Reference Resolution"
status: completed
effort: "3-4 days"
---

# Phase 2: Implement Structured Reference Resolution

## Overview

Make AI responsible for identity, preparation, and quantity extraction while
local `food_reference` and one selected FatSecret detail record own macros.
Reuse the existing staged provider port and `NutritionResolver`; keep
`ParseMealTextHandler` as orchestration and preserve the public DTO.

**Priority:** P1
**Depends on:** Phase 1

## Context Links

- [Phase 1](./phase-01-characterize-parse-text-nutrition-contracts.md)
- `src/infra/adapters/fat_secret_service.py`
- `src/domain/ports/nutrition_reference_provider_port.py`
- `src/domain/services/nutrition_resolver.py`
- `src/app/services/food_reference_validation_service.py`
- `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- `src/api/dependencies/event_bus.py`

## Key Insights

- `FatSecretService` already exposes `search_food_candidates()` and
  `get_food_details()`; calling `search_foods()` fetches details for every hit.
- `NutritionReferenceProviderPort` already models the desired staged boundary.
- `NutritionResolver` already scales structured per-100g macros and derives
  calories, but needs reusable validation/scoring behavior.
- The composition root already has a batched normalized `food_reference` lookup
  closure, so parse-text can use local references without adding a repository
  dependency to the handler.

## Requirements

- Extend the internal AI contract with optional canonical English lookup name,
  explicit preparation (`raw`, `boiled`, `baked`, `fried`, `mashed`, or
  `unknown`), and `quantity_g`; normalize older/missing values safely.
- Preserve localized display name, `quantity`, and `unit` in the response.
- Preserve preparation across lookup. A prepared request may use a local row
  only when the row's original name explicitly matches that preparation;
  otherwise bypass the preparation-collapsing normalized key and query
  FatSecret with the preparation term. `unknown` may use a generic unprepared
  row but not a conflicting prepared row.
- Batch exact normalized local lookup once per request; accept only verified,
  complete records whose origin maps to the existing public values: USDA-like
  origins -> `usda`, FatSecret origins -> `fatsecret`; unknown origins bypass
  local resolution rather than widening the API value set.
- On a local miss, search bounded FatSecret candidates, score deterministically,
  and fetch details for only the selected candidate.
- Define one mapped-detail contract. Calories/protein/carbs/fat and a positive
  metric basis are required numeric/non-negative fields; fiber/sugar are
  optional numeric/non-negative fields and are mapped when the provider offers
  them. Reuse the existing trusted-reference `protein+carbs+fat <= 110g`
  tolerance; do not add fiber/sugar-versus-carb rejection that contradicts
  existing verified-reference tests. Provider energy must be within
  `max(20 kcal, 20%)` of backend-derived energy, with missing fiber explicitly
  represented as unavailable/zero in that comparison.
- Scale accepted reference macros by `quantity_g / 100` or existing verified
  unit conversion; derive calories from `Macros` only.
- Carry resolved fiber/sugar through `ParsedFoodItemDto` and the existing public
  fields so route calories use the same fiber value for authenticated and guest
  responses.
- Legacy description parsing may run only when structured fields are absent and
  must pass the same validator before claiming FatSecret.
- Use one request-wide AI state machine capped at two total generations. Schema
  repair consumes the only retry. Semantic repair is one whole-request retry
  only when the first output was schema-valid; preserve per-request reference
  results and never retry per item. Provider miss/outage alone does not retry AI.
- Accept fallback only after quantity-aware density checks. High-density
  exceptions must be explicit and tested for oils, fats, nuts/seeds, and dry
  concentrates. Otherwise raise the existing 422 error.
- Bound all reference work per request: five searches, five details, concurrency
  three, deterministic input-order admission, and a single request-wide deadline
  from `PARSE_TEXT_FATSECRET_TIMEOUT_SECONDS` (default three seconds). Cancel
  unfinished calls; remaining items take validated fallback or controlled 422.
- Bound `current_items` before prompt construction: at most 20 documented item
  shapes, bounded strings/nesting, and 12 KiB serialized total. Reject unknown
  nested prompt content before any AI/provider call without changing normal
  client payload shape.
- Cap accepted provider serving metadata to 12 normalized entries, 100-character
  labels/descriptions, finite positive weights, and no control characters.
- Never use AI-vs-provider divergence as proof that the AI estimate is correct.

## Architecture And Data Flow

```text
AI extraction -> internal lookup_name/preparation/quantity_g + provisional macros
       -> one batched verified local exact lookup
       -> miss: FatSecret candidate search -> deterministic score -> one detail
       -> structured validator -> scale macros -> backend calorie derivation
       -> unresolved: one bounded AI semantic retry -> validate or controlled 422
       -> unchanged ParseMealTextResponse mapping
```

`NutritionResolver` owns pure normalization, scoring, validation, and scaling.
The handler owns timeouts, fallbacks, source assignment, and aggregation. The
composition root owns DB/provider construction.

`NutritionResolver` currently has no production consumer; Phase 2 deliberately
adds its first one. This is a new production seam, protected by a default-off
`PARSE_TEXT_STRUCTURED_REFERENCE_ENABLED` rollback flag until staging gates pass.
Do not change `FatSecretService.search_foods()` semantics or any meal-suggestion
consumer; parse-text calls only the existing staged methods.

## Related Code Files

Modify:

- `src/domain/services/prompts/system_prompts.py`
- `src/domain/model/ai/nutrition_contracts.py`
- `src/domain/services/nutrition_resolver.py`
- `src/app/schemas/meal_schemas.py`
- `src/app/handlers/command_handlers/meal_text_parsing_utils.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/api/schemas/request/meal_requests.py`
- `src/api/dependencies/event_bus.py`
- `src/domain/services/prompts/input_sanitizer.py`
- `src/infra/adapters/fat_secret_service.py`
- `tests/unit/domain/services/test_nutrition_resolver.py`
- `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`
- `tests/unit/api/test_event_bus_dependency_singletons.py`
- `tests/unit/infra/adapters/test_fat_secret_service.py`
- focused sanitizer/privacy tests located during implementation

Do not modify public response schemas, route files, DB models/migrations, mobile,
meal image analysis, or meal-suggestion runtime behavior.

## Implementation Steps

1. **Tests Before:** run Phase 1 green tests; run each semantic test and confirm
   its expected red reason before editing runtime code.
2. Add internal extraction fields and prompt rules. Unknown preparation stays
   `unknown`; never invent cooked state. Preserve tolerant parsing for old
   flat-macro fixtures while emitting the canonical nested schema.
3. Extend `NutritionResolver` with pure, typed helpers for preparation-aware
   name matching,
   candidate scoring, reference validation, density fallback validation, and
   scaling. Reuse `Macros`; do not import infrastructure into domain.
4. Refactor the handler to batch local references before its item loop and pass
   matches into its resolution shell.
5. Replace the handler's `search_foods()` call with staged provider calls under
   the request deadline/call semaphore. Do not modify `search_foods()` semantics;
   reject no-match/tie-below-threshold candidates instead of accepting index 0.
6. Map accepted local origin source or FatSecret source truthfully; retain
   `ai_estimate` for a real fallback. Invalid/incomplete detail records may not
   set FatSecret source or leak their allowed units. Map optional fiber/sugar
   and bound all serving metadata at the provider-to-client boundary.
7. Wire the existing batch lookup and staged provider through
   `get_configured_event_bus()`; update singleton wiring fakes and constructor
   assertions for the one production plus six direct unit constructions. Add
   the default-off rollback flag and verify legacy behavior when disabled.
8. Implement the two-generation request state machine and compact semantic
   feedback without raw provider payloads. Cache request-local resolution work;
   exhaustion raises `AIOutputValidationError` with bounded reason codes.
9. Validate/bound `current_items` before JSON prompt construction. Remove raw
   text/query/payload snippets from sanitizer/FatSecret logs; add captured-log
   canaries covering every target failure path.
10. **Refactor:** remove the old AI-divergence acceptance rule. Keep description
   parsing as an isolated compatibility fallback, then pass through validation.
11. **Tests After:** turn Phase 1 semantic tests green and add preparation-pair,
    source-map, fiber/sugar, metadata-bound, token-normalization,
    preparation, branded/generic, tie, local-hit, timeout, invalid-detail,
    high-density exception, max-item budget, cancellation, feature-flag, and
    multi-item batch cases. Re-run shared FatSecret and meal validation consumers.
12. **Regression Gate:** format/lint/type-check changed modules and run focused
    unit suites below.

```bash
pytest tests/unit/domain/services/test_nutrition_resolver.py -v
pytest tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -v
pytest tests/unit/api/test_event_bus_dependency_singletons.py tests/unit/api/test_guest_parse_trial.py tests/unit/api/test_routes_with_mocked_event_bus.py -v
pytest tests/unit/infra/adapters/test_fat_secret_service.py tests/unit/app/services/test_food_reference_validation_service.py -v
ruff format --check src/domain/services/nutrition_resolver.py src/app/handlers/command_handlers/meal_text_parsing_utils.py src/app/handlers/command_handlers/parse_meal_text_handler.py src/api/dependencies/event_bus.py tests/unit/domain/services/test_nutrition_resolver.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py
ruff check src/domain/services/nutrition_resolver.py src/app/handlers/command_handlers/meal_text_parsing_utils.py src/app/handlers/command_handlers/parse_meal_text_handler.py src/api/dependencies/event_bus.py tests/unit/domain/services/test_nutrition_resolver.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py
mypy src/domain/services/nutrition_resolver.py src/app/handlers/command_handlers/parse_meal_text_handler.py
```

## Todo List

- [x] Add and test internal identity/preparation/quantity fields.
- [x] Add pure scoring, validation, scaling, and fallback guards.
- [x] Batch local lookup and stage FatSecret search/detail.
- [x] Add request-wide budgets, bounded semantic retry, and controlled failure.
- [x] Preserve fiber/sugar and map existing public source values.
- [x] Bound refinement/serving metadata and remove transitive raw logs.
- [x] Add default-off rollback wiring without changing shared FatSecret callers.
- [x] Update the one production and six direct unit handler constructions.
- [x] Make every Phase 1 semantic test green.

## Success Criteria

- [x] `100gr khoai tay` cannot return the 890-kcal fallback payload.
- [x] A confident structured reference replaces provisional AI macros.
- [x] Wrong-first and ambiguous candidates do not win by provider ordering.
- [x] One resolved provider miss uses at most one search plus one detail call.
- [x] Invalid structured details never claim FatSecret.
- [x] Existing response keys, routes, units, localization, and 422 mapping remain
  compatible for authenticated and guest callers.

## Risk Assessment

- **Over-strict matching:** keep identity confidence separate from macro
  validity, retain preparation in matching, and reuse the existing 110 g
  reference tolerance; fall back rather than select a weak candidate.
- **Legitimate dense foods:** explicit tested density exceptions prevent oils,
  fats, nuts, and dry concentrates from being rejected as potatoes.
- **Latency:** local batch first, request-wide 5/5 call caps, concurrency three,
  one deadline, no AI adjudicator, and a max-item slow-provider test.
- **Shared service regression:** do not change `IngredientNutritionResolver` or
  `NutritionLookupService` behavior; reuse their patterns and shared domain seam.

## Security And Privacy

- Sanitize user text before AI as today.
- Log only bounded reason/source/count fields; never raw text, prompt, candidate
  payload, provider token, or detail response.
- Captured-log canaries cover existing sanitizer and FatSecret error paths; a
  handler-only logging assertion is insufficient.
- Keep provider credentials and repository construction in infrastructure/API
  composition, outside the domain resolver.

## Next Steps

Phase 3 begins only after focused tests, formatting, lint, and type checks pass.
